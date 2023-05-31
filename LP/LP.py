from gurobipy import *





if __name__ == '__main__':
    
    ##### Model #####
    
    model = Model('model')
    
    
    
    
    
    ##### Parameters #####
    
    ''' Adjust size of the parking lot '''
    B = 160.0       # Width of the parking lot
    L = 90.0       # Length of the parking lot (Length of exterior rows)
    w = 7.0         # Width of the road at top and bottom
    l = L - 2*w     # Length of interior rows
    q = 1.00        # Adjust the road width among parking rows
    '''--------------------------------'''
    
    ''' Adjust angles of a parking spot row '''   
    num_of_angles = 5
    angle_set = [90, 75, 60, 45, 30]
    '''-------------------------------------''' 
    
    ''' Change parameters here if angles changed '''
    A2 = [2.50, 2.70, 2.80, 3.50, 5.60]
    C1 = [5.00, 5.50, 5.60, 5.30, 4.50]
    C3 = [5.00, 5.15, 5.05, 4.40, 3.40]
    D  = [q*7.00, q*6.00, q*4.50, q*3.75, q*3.50]
    F1 = [C1[i] + C3[i] + D[i] for i in range(num_of_angles)]
    F3 = [2*C3[i] + D[i] for i in range(num_of_angles)]
    '''------------------------------------------'''
    
    
    
    
    
    ##### Variables #####
    
    # angle set = [90, 75, 60, 45, 30]
    X = []
    Xe = []
    E = []
    n = []
    ne = []
    nEE = []
    for i in range(num_of_angles):
        X.append(model.addVar(lb=0, vtype=GRB.INTEGER, name='X'+str(angle_set[i])))
        Xe.append(model.addVar(lb=0, vtype=GRB.INTEGER, name='Xe'+str(angle_set[i])))
        E.append(model.addVar(lb=0, vtype=GRB.INTEGER, name='E'+str(angle_set[i])))
        n.append(model.addVar(lb=0, vtype=GRB.INTEGER, name='n'+str(angle_set[i])))
        ne.append(model.addVar(lb=0, vtype=GRB.INTEGER, name='ne'+str(angle_set[i])))
        nEE.append(model.addVar(lb=0, vtype=GRB.INTEGER, name='nEE'+str(angle_set[i])))
        
        
        
        
        
    ##### Objective #####
    
    # Maximize the total number of parking spots
    model.setObjective(
        quicksum(n[i] + ne[i] + nEE[i] for i in range(num_of_angles)),
        GRB.MAXIMIZE)
    
    
    
    
    
    ##### Constraints #####
    
    # Total width of full interior rows, full exterior rows, and exterior rows should be less than the width of  the parking lot
    model.addConstr(quicksum(F3[i]*X[i] + F1[i]*Xe[i] + (C1[i]+D[i])*E[i] for i in range(num_of_angles)) <= B)
    
    # The number of spots in each rows should be less than its upper bound
    # Upper bound = (max length of row / width of a spot) * number of rows
    model.addConstrs(l//A2[i]*2*X[i] >= n[i] for i in range(num_of_angles))
    model.addConstrs(l//A2[i]*Xe[i] + L//A2[i]*Xe[i] >= ne[i] for i in range(num_of_angles))
    model.addConstrs(L//A2[i]*E[i] >= nEE[i] for i in range(num_of_angles))
    
    # There should be exactly two exterior rows
    model.addConstr(quicksum(Xe[i] + E[i] for i in range(num_of_angles)) == 2)
    
    
    
    
    
    ##### Optimization #####
    
    model.optimize()
    
    
    
    
    
    ##### Results #####
    
    results = open('LP_160x90_000.csv', 'w')
    
    results.write(f'B, {B}')
    results.write(f'\nL, {L}')
    results.write(f'\nw, {w}')
    results.write(f'\nq, {q}')
    
    results.write(f'\nobj. value, {model.objVal}')
    
    results.write(f'\nvar\\angle')
    for i in range(num_of_angles):
        results.write(f',{angle_set[i]}')
        
    results.write(f'\nX')
    for i in range(num_of_angles):
        results.write(f',{X[i].x}')
        
    results.write(f'\nXe')
    for i in range(num_of_angles):
        results.write(f',{Xe[i].x}')
        
    results.write(f'\nE')
    for i in range(num_of_angles):
        results.write(f',{E[i].x}')
        
    results.write(f'\nn')
    for i in range(num_of_angles):
        results.write(f',{n[i].x}')
        
    results.write(f'\nne')
    for i in range(num_of_angles):
        results.write(f',{ne[i].x}')
        
    results.write(f'\nnEE')
    for i in range(num_of_angles):
        results.write(f',{nEE[i].x}')
    
    results.close()
    
    '''
    X_results = []
    Xe_results = []
    E_results = []
    n_results = []
    ne_results = []
    nEE_results = []
    for i in range(num_of_angles):
        X_results.append(X[i].x)
        Xe_results.append(Xe[i].x)
        E_results.append(E[i].x)
        n_results.append(n[i].x)
        ne_results.append(ne[i].x)
        nEE_results.append(nEE[i].x)
    '''
   
    
    
    
    
