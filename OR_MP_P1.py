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
    time_unit = timedelta(minutes=30)
    
    # Basic info
    n_S = Instance['n_S']
    n_C = Instance['n_C']
    n_L = Instance['n_L']
    n_K = Instance['n_K']
    n_D = Instance['n_D']
    B = int(Instance['B']/30)
    
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
            order_begin_time.append(int(0))
            order_end_time.append(int(0))
            continue
        order_level.append(Instance['Order_Info'][i-1][1])
        order_initial_station.append(Instance['Order_Info'][i-1][2])
        order_final_station.append(Instance['Order_Info'][i-1][3])
        begin_time = (Instance['Order_Info'][i-1][4] - datetime.strptime('2023/01/01 00:00:00', '%Y/%m/%d %H:%M:%S')) / time_unit
        end_time = (Instance['Order_Info'][i-1][5] - datetime.strptime('2023/01/01 00:00:00', '%Y/%m/%d %H:%M:%S')) / time_unit
        order_begin_time.append(int(begin_time))
        order_end_time.append(int(end_time))  
    
    # Station distance [i][j] = moving time needed from station i to j
    station_distance = []
    for i in range(n_S+1):
        station_distance.append([])
        for j in range(n_S+1):
            if (i == 0 or j == 0):
                station_distance[i].append(float(0))
            else:
                station_distance[i].append(float(Instance['Station_Distance'][(i-1)*n_S+(j-1)][2]))
    
    # Revenue [k] = revenue of order k 
    revenue = []
    for i in range(n_K+1):
        rent_time = (order_end_time[i] - order_begin_time[i])/2
        revenue.append(level_rate[order_level[i]] * rent_time)
    
    # Moving time [i][j][k] = moving time needed for car i to serve for order k after served order j
    moving_time = []
    for i in range(n_C):
        moving_time.append([])
        for j in range(n_K+1):
            moving_time[i].append([])
            if (j == 0):
                for k in range(n_K+1):
                    if (j == k or k == 0):
                        moving_time[i][j].append(int(0))
                    else:
                        # NO moving time needed for the first order as car i is at the correct station required by the first order
                        if (station_distance[car_initial_station[i]][order_initial_station[k]] == 0):
                            moving_time[i][j].append(int(0))
                        # moving time needed for the first order, 30min ready time added
                        else:
                            moving_time[i][j].append(int((station_distance[car_initial_station[i]][order_initial_station[k]]+30) / 30))  
            else:
                for k in range(n_K+1):
                    # can NOT accept same order twice and NO moving time needed after the last order 
                    if (j == k or k == 0):
                        moving_time[i][j].append(int(0))
                    else:
                        moving_time[i][j].append(int(station_distance[order_final_station[j]][order_initial_station[k]] / 30)) 
    
    
    
    ##### Variables #####
    # accept_k: binary, 1 if order k is accepted
    accept = []
    for i in range(n_K+1):
        accept.append(P1.addVar(lb=0, vtype=GRB.BINARY, name='accept_'+str(i+1)))
        
    # u_k: binary, 1 if order k is upgraded
    u = []
    for i in range(n_K+1):
        u.append(P1.addVar(lb=0, vtype=GRB.BINARY, name='u_'+str(i+1)))    
        
    # x_ijk: binary, 1 if order k is processed directly after order j on car i
    x = []
    for i in range(n_C):
        x.append([])
        for j in range(n_K+1):
            x[i].append([])
            for k in range(n_K+1):
                x[i][j].append(P1.addVar(lb=0, vtype=GRB.BINARY, name='x_'+str(i+1)+str(j)+str(k)))
                
 
    
    ##### Objective #####    
    P1.setObjective(
        quicksum(accept[k]*revenue[k] - (1-accept[k])*2*revenue[k] for k in range(1, n_K+1)),
        GRB.MAXIMIZE)
    
    
    
    ##### Constraints #####
    # order 0 is always accepted (all cars start with order 0 and end with order 0)
    P1.addConstr(accept[0] == 1)
    
    # (may be taken away) we can NOT accept same order twice or more
    P1.addConstrs(x[i][j][j] == 0 for i in range(n_C) for j in range(n_K+1))
    
    # car i has to select exactly one order k to start serving, or NEVER serves for any order
    P1.addConstrs(quicksum(x[i][0][k] for k in range(1, n_K+1)) <= 1 for i in range(n_C))
    
    # (may be taken away) if car i starts to serve, it has to end serving
    P1.addConstrs(quicksum(x[i][0][k] for k in range(1, n_K+1)) == quicksum(x[i][j][0] for j in range(1, n_K+1)) for i in range(n_C))
    
    # for an order j served by car i, it has a predecessor order h and a successor order k on the same car 
    P1.addConstrs(quicksum(x[i][j][k] for k in range(n_K+1) if (k!=j)) == quicksum(x[i][h][j] for h in range(n_K+1) if (h!=j)) for i in range(n_C) for j in range(1, n_K+1))
    
    # (may be taken away) we can NOT serve for order k after order j and serve for order j after order k at the same time
    P1.addConstrs(1-x[i][j][k] >= x[i][k][j] for i in range(n_C) for j in range(1, n_K+1) for k in range(1, n_K+1))
    
    # (may be taken away) if order j served by car i is either the first order, the last order or both, it can only have order 0 as its predecessor, successor, or both, respectively 
    P1.addConstrs(2-x[i][0][j]-x[i][j][0] >= quicksum(x[i][j][k] for k in range(1, n_K+1))+quicksum(x[i][h][j] for h in range(1, n_K+1)) for i in range(n_C) for j in range(1, n_K+1))
    
    # if order k is accepted, exactly one car i serves for it
    P1.addConstrs(quicksum(quicksum(x[i][j][k] for i in range(n_C)) for j in range(n_K+1) if (j!=k)) == accept[k] for k in range(1, n_K+1))
    
    # if order j is accepted, exactly one car i serves for it
    P1.addConstrs(quicksum(quicksum(x[i][j][k] for i in range(n_C)) for k in range(n_K+1) if (k!=j)) == accept[j] for j in range(1, n_K+1))
    
    # if order j can be accepted after upgraded, upgrade it
    P1.addConstrs(accept[j]*(u[j]*(order_level[j]+1)+(1-u[j])*order_level[j]) == quicksum(car_level[i]*x[i][j][k] for i in range(n_C) for k in range(n_K+1) if (k!=j)) for j in range(1, n_K+1))
    
    # if order k can be accepted after upgraded, upgrade it
    P1.addConstrs(accept[k]*(u[k]*(order_level[k]+1)+(1-u[k])*order_level[k]) == quicksum(car_level[i]*x[i][j][k] for i in range(n_C) for j in range(n_K+1) if (j!=k)) for k in range(1, n_K+1))
    
    # moving time needed for car i to serve its first order(ready time already included) <= the begin time required
    P1.addConstrs(x[i][0][j]*moving_time[i][0][j] <= order_begin_time[j] for i in range(n_C) for j in range(1, n_K+1))
    
    # the begin time of order k >= the end time of order j + total setup time for car i to serve order k after order j
    P1.addConstrs(order_begin_time[k] + n_D*100000*(1-x[i][j][k]) >= order_end_time[j] + 2 + 6 + moving_time[i][j][k] + 1 for i in range(n_C) for j in range(1, n_K+1) for k in range(1, n_K+1) if (j!=k))
    
    # total moving time of all cars <= B
    P1.addConstr(quicksum(x[i][j][k]*moving_time[i][j][k] for i in range(n_C) for j in range(n_K+1) for k in range(1, n_K+1)) <= B)
    
    
    
    ##### Optimization #####
    P1.optimize()
    
    print("Obj. value = ", P1.objVal)
    
    ac_results = []
    for i in range(n_K+1):
        ac_results.append(accept[i].x)
        
    u_results = []
    for i in range(n_K+1):
        u_results.append(u[i].x)
        
    x_results = []
    for i in range(n_C):
        x_results.append([])
        for j in range(n_K+1):
            x_results[i].append([])
            for k in range(n_K+1):
                x_results[i][j].append(x[i][j][k].x)
    
    
    
