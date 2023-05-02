import numpy as np
from datetime import *
from gurobipy import *

# Store all parameters of an instance into a dict
def ReadInstance(filepath):
    
    key_list = ['n_S', 'n_C', 'n_L', 'n_K', 'n_D', 'B', 'Car_Info', 'Level_Rate', 'Order_Info', 'Station_Distance']
    Instance = {key: None for key in key_list}
    fh = open(filepath, 'r', encoding='utf-8-sig')
    
    # Part1
    fh.readline()
    line = []
    line = fh.readline().split(',')
    Instance['n_S'] = int(line[0])
    Instance['n_C'] = int(line[1])
    Instance['n_L'] = int(line[2])
    Instance['n_K'] = int(line[3])
    Instance['n_D'] = int(line[4])
    Instance['B'] = int(line[5])
    fh.readline()
    
    # Part2
    fh.readline()
    Instance['Car_Info'] = []
    for i in range(Instance['n_C']):
        car = []
        car = np.array(fh.readline().split(',')).astype(int)
        Instance['Car_Info'].append(car)
    fh.readline()
    
    # Part3
    fh.readline()
    Instance['Level_Rate'] = []
    for i in range(Instance['n_L']):
        level = []
        level = np.array(fh.readline().split(',')).astype(int)
        Instance['Level_Rate'].append(level)
    fh.readline()
    
    # Part4
    fh.readline()
    Instance['Order_Info'] = []
    for i in range(Instance['n_K']):
        order = []
        order = fh.readline().split(',')
        for j in range(4):
            order[j] = int(order[j])
        order[4] = datetime.strptime(order[4].rstrip()+':00', '%Y/%m/%d %H:%M:%S')
        order[5] = datetime.strptime(order[5].rstrip()+':00', '%Y/%m/%d %H:%M:%S')
        Instance['Order_Info'].append(np.array(order))
    fh.readline()
        
    # Part5
    fh.readline()
    Instance['Station_Distance'] = []
    for i in range(Instance['n_S'] * Instance['n_S']):
        distance = []
        distance = np.array(fh.readline().split(',')).astype(int)
        Instance['Station_Distance'].append(distance)
    fh.readline()
        
    fh.close()
    
    return Instance
    
# Main 
if __name__=='__main__':
    
    ##### Get instance #####
    filepath = 'data/instance05.txt'
    Instance = ReadInstance(filepath)
    
    
    
    ##### Model #####
    P1 = Model('P1')
    
    
    
    ##### Parameters #####
    # Basic info
    n_S = Instance['n_S']
    n_C = Instance['n_C']
    n_L = Instance['n_L']
    n_K = Instance['n_K']
    n_D = Instance['n_D']
    B = Instance['B']
    
    # Car info
    car_level = []
    car_initial_station = []
    for i in range(n_C):
        car_level.append(Instance['Car_Info'][i][1])
        car_initial_station.append(Instance['Car_Info'][i][2])
        
    # Level rate
    level_rate = []
    for i in range(n_L+1):
        if (i == 0):
            level_rate.append(int(0))
            continue
        level_rate.append(Instance['Level_Rate'][i-1][1])
        
    # Order info
    order_level = []
    order_initial_station = []
    order_final_station = []
    order_begin_time = []
    order_end_time = []
    for i in range(n_K+1):
        if (i == 0):
            order_level.append(int(0))
            order_initial_station.append(int(0))
            order_final_station.append(int(0))
            order_begin_time.append(float(0))
            order_end_time.append(float(0))
            continue
        order_level.append(Instance['Order_Info'][i-1][1])
        order_initial_station.append(Instance['Order_Info'][i-1][2])
        order_final_station.append(Instance['Order_Info'][i-1][3])
        begin_time = (Instance['Order_Info'][i-1][4] - datetime.strptime('2023/01/01 00:00:00', '%Y/%m/%d %H:%M:%S')) / timedelta(hours=1)
        end_time = (Instance['Order_Info'][i-1][5] - datetime.strptime('2023/01/01 00:00:00', '%Y/%m/%d %H:%M:%S')) / timedelta(hours=1)
        order_begin_time.append(float(begin_time))
        order_end_time.append(float(end_time))
    
    # Station distance
    station_distance = []
    for i in range(n_S+1):
        station_distance.append([])
        for j in range(n_S+1):
            if (i == 0 or j == 0):
                station_distance[i].append(int(0))
            else:
                station_distance[i].append(Instance['Station_Distance'][(i-1)*n_S+(j-1)][2])
    
    # Revenue
    revenue = []
    for i in range(n_K+1):
        rent_time = order_end_time[i] - order_begin_time[i]
        revenue.append(level_rate[order_level[i]] * rent_time)
    
    
    
    ##### Variables #####
    # accept_k: binary, 1 if order k is accepted
    accept = []
    for i in range(n_K+1):
        if (i == 0):
            accept.append(P1.addVar(lb=1, vtype=GRB.BINARY, name='accept_'+str(i+1)))
            continue
        accept.append(P1.addVar(lb=0, vtype=GRB.BINARY, name='accept_'+str(i+1)))
        
    # x_ijk: binary, 1 if order k is processed directly after order j on car i
    x = []
    for i in range(n_C):
        x.append([])
        for j in range(n_K+1):
            x[i].append([])
            for k in range(n_K+1):
                x[i][j].append(P1.addVar(lb=0, vtype=GRB.BINARY, name='x_'+str(i+1)+str(j)+str(k)))
                
    # u_k: binary, if order k is upgraded
    u = []
    for i in range(n_K+1):
        u.append(P1.addVar(lb=0, vtype=GRB.BINARY, name='u_'+str(i+1)))
                
    # s_ijk: continuous, moving time for car i to process order k after finish order j
    s = []
    for i in range(n_C):
        s.append([])
        for j in range(n_K+1):
            s[i].append([])
            for k in range(n_K+1):
                s[i][j].append(P1.addVar(lb=0, vtype=GRB.CONTINUOUS, name='s_'+str(i+1)+str(j)+str(k)))
    
    ##### Objective #####    
    P1.setObjective(
        quicksum(accept[k]*revenue[k] - (1-accept[k])*2*revenue[k] for k in range(1, n_K+1)),
        GRB.MAXIMIZE)
    
    
    
    ##### Constraints #####
    # x_ijk = 1 implies order j and k are both accepted
    P1.addConstrs((2*x[i][j][k] <= accept[j] + accept[k] for j in range(n_K+1) for k in range(1, n_K+1) if (j!=k) for i in range(n_C)))
    
    # an order can only be processed by one car
    P1.addConstrs((quicksum(quicksum(x[i][j][k] for i in range(n_C)) for j in range(n_K+1) if (j!=k)) == 1 for k in range(1, n_K+1)))
    P1.addConstrs((quicksum(quicksum(x[i][j][k] for i in range(n_C)) for k in range(n_K+1) if (k!=j)) == 1 for j in range(1, n_K+1)))
    P1.addConstrs((quicksum(x[i][j][k] for k in range(n_K+1) if (k!=j)) == quicksum(x[i][h][j] for h in range(n_K+1) if (h!=j)) for j in range(1, n_K+1) for i in range(n_C)))
    
    # car i process its first order
    P1.addConstrs((quicksum(x[i][0][j] for j in range(1, n_K+1)) <= 1 for i in range(n_C)))
    
    # (upgrade) level of car i must match to level required of order k or +1
    P1.addConstrs((x[i][j][k]*car_level[i] <= u[j] + order_level[j] for j in range(1, n_K+1) for k in range(1, n_K+1) if (j!=k) for i in range(n_C)))
    P1.addConstrs((x[i][j][k]*car_level[i] <= u[k] + order_level[k] for k in range(1, n_K+1) for j in range(1, n_K+1) if (k!=j) for i in range(n_C)))
    
    # moving time for car i to process its first order
    P1.addConstrs((s[i][0][j] == station_distance[car_initial_station[i]][order_initial_station[j]] for j in range(1, n_K+1) for i in range(n_C)))
    
    # moving time for car i to process order k after order j
    P1.addConstrs((s[i][j][k] == station_distance[order_final_station[j]][order_initial_station[k]] for j in range(1, n_K+1) for k in range(1, n_K+1) if (j!=k) for i in range(n_C)))
    
    # (time) proper schedule
    P1.addConstrs((x[i][j][k] * (order_end_time[j]+3+s[i][j][k]+0.5) <= order_begin_time[k] for j in range(n_K+1) for k in range(1, n_K+1) if (j!=k) for i in range(n_C)))
    
    ##### Optimization #####
    P1.optimize()
    

    
