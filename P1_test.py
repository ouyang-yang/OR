from gurobipy import *
import pandas as pd
import numpy as np
import grblogtools as glt
from scipy.spatial.distance import squareform, pdist
import datetime
import math

df = pd.read_csv('data\instance05.txt', header=None)

df_main = df.iloc[:2,:]
df_main.columns = df_main.iloc[0]
df_main = df_main[1:]
n_S = int(df_main['n_S'])
n_C = int(df_main['n_C'])
n_L = int(df_main['n_L'])
n_K = int(df_main['n_K'])
n_D = int(df_main['n_D'])
B = int(df_main['B'])//30

df_car =  df.iloc[3:n_C+4,:]
df_car.columns = df.iloc[3,:]
df_car = df_car.dropna(axis=1)
df_car = df_car[1:]
df_car = df_car.reset_index(drop=True)

car_current_station = []
for m in range(n_C):
    initial_station = int(df_car.loc[m, 'Initial station'])
    car_current_station.append(initial_station)

df_car_lv = df.iloc[n_C+5:n_C+n_L+6,:]
df_car_lv.columns = df_car_lv.iloc[0]
df_car_lv = df_car_lv.dropna(axis=1)
df_car_lv = df_car_lv[1:]
df_car_lv = df_car_lv.reset_index(drop=True)

df_order = df.iloc[n_C+n_L+7:n_C+n_L+n_K+8,:]
df_order.columns = df_order.iloc[0]
df_order = df_order.dropna(axis=1)
df_order = df_order[1:]
df_order['Time span'] = df_order.apply(lambda row: pd.to_datetime(row['Return time']) - pd.to_datetime(row['Pick-up time']), axis=1)
df_order['Time units'] = df_order['Time span'].apply(lambda x: math.ceil(x.total_seconds() / 1800))
first_period_start = pd.to_datetime('2023/01/01 00:00')
time_unit = pd.Timedelta('30 minutes')
df_order['Pick-up time (ordinal)'] = df_order.apply(lambda row: pd.to_datetime(row['Pick-up time']) - first_period_start, axis=1).apply(lambda x: math.ceil(x.total_seconds() / 1800))
df_order['Return time (ordinal)'] = df_order.apply(lambda row: pd.to_datetime(row['Return time']) - first_period_start, axis=1).apply(lambda x: math.ceil(x.total_seconds() / 1800))
df_order = pd.merge(df_order, df_car_lv, left_on='Level', right_on='Car level', how='left')
df_order = df_order.drop(['Car level'], axis=1)

# pickup station of order k
pickup = []
for k in range(n_K+1):
    if (k==0):
        pickup.append(int(0))
        continue
    pickup_station = int(df_order.loc[k-1, 'Pick-up station'])
    pickup.append(pickup_station)
# return station of order k
finish = []
for k in range(n_K+1):
    if (k==0):
        finish.append(int(0))
        continue
    return_station = int(df_order.loc[k-1, 'Return station'])
    finish.append(return_station)

df_distance = df.iloc[n_C+n_L+n_K+9:n_C+n_L+n_K+n_S**2+10,:]
df_distance.columns = df_distance.iloc[0]
df_distance = df_distance.dropna(axis=1)
df_distance = df_distance[1:]
distance = df_distance.pivot(index='From', columns='To', values='Distance')
distance = distance.apply(pd.to_numeric, errors='coerce') // 30
distance_array = distance.values

Cmax = 48*n_D

P1 = Model("P1")
#-------- Add variables as a list ---------#
# accept_k=1 if order k is accepted; accept_k=0 o.w.
accept = []
for k in range(n_K+1):
    if (k == 0):
        accept.append(int(1))
        continue
    accept.append(P1.addVar(lb=0, vtype=GRB.BINARY, name='accept_'+str(k)))

# z_mpq = 1 if order p and order q are on car m and order p is before order q
z = []
for m in range(n_C):
    z.append([])
    for p in range(n_K+1):
        z[m].append([])
        for q in range(n_K+1):
            z[m][p].append(P1.addVar(lb = 0, vtype = GRB.BINARY, name = "z_" + str(m+1) + str(p) + str(q)))

# x_mk = time spent when accept order k assigned to car m (rental time)
x = []
for m in range(n_C):
    x.append([])
    for k in range(n_K+1):
        if (k==0):
            x[m].append(int(0))
            continue
        time_units = int(df_order.loc[k-1, 'Time units'])
        x[m].append(P1.addVar(lb = time_units, vtype = GRB.INTEGER, name = "x_" + str(m+1) + str(k)))

# Ck = completion time of order k
C = []
for k in range(n_K+1):
    if (k==0):
        C.append(int(0))
        continue   
    C.append(P1.addVar(lb=0, vtype = GRB.INTEGER, name = "C_" + str(k)))

# Om = latest completion time of orders on car m
O = []
for m in range(n_C):
    O.append(P1.addVar(lb=0, vtype = GRB.INTEGER, name = "O_" + str(m+1)))

# s_mpq: setup time for car m to process order q after finish order p
s = []
for m in range(n_C):
    s.append([])
    for p in range(n_K+1):
        s[m].append([])
        for q in range(n_K+1):
            s[m][p].append(P1.addVar(lb=0, vtype=GRB.INTEGER, name='s_'+str(m+1)+str(p)+str(q)))

# Revenue_k = revenue of order k
Revenue = []
for k in range(n_K+1):
    if (k==0):
        Revenue.append(int(0))
        continue
    time_units = int(df_order.loc[k-1, 'Time units'])
    hour_rate = int(df_order.loc[k-1, 'Hour rate'])
    Revenue.append(time_units * hour_rate)

A = P1.addVar(lb = 100000, vtype = GRB.INTEGER, name = "a large number")

P1.setObjective(
    quicksum(accept[k]*Revenue[k] - (1-accept[k])*2*Revenue[k] for k in range(1, n_K+1)),
    GRB.MAXIMIZE)

P1.addConstrs((2*z[m][p][q] <= accept[p] + accept[q] for p in range(n_K+1) for q in range(n_K+1) if (p!=q) for m in range(n_C)))
P1.addConstrs((quicksum(z[m][p][q] for m in range(n_C) for p in range(n_K+1) if (p!=q)) == 1) for q in range(1, n_K+1))
P1.addConstrs((quicksum(z[m][p][q] for m in range(n_C) for q in range(n_K+1) if (p!=q)) == 1) for p in range(1, n_K+1))
P1.addConstrs((quicksum(z[m][0][p] for p in range(1, n_K+1)) <= 1 for m in range(n_C)))
P1.addConstrs((quicksum(z[m][p][q] for q in range(n_K+1) if (p!=q)) == quicksum(z[m][h][p] for h in range(n_K+1) if (h!=p))) for p in range(n_K) for m in range(n_C))
P1.addConstrs((C[q]-C[p] + A*(1-z[m][p][q]) >= s[m][p][q] + x[m][q]) for p in range(n_K+1) for q in range(n_K) if (p!=q) for m in range(n_C))
P1.addConstrs(C[0] == 0 for m in range(n_C))
P1.addConstrs((quicksum(((s[m][p][q] + x[m][q]) * z[m][p][q]) for q in range(n_K) for p in range(n_K+1) if (p!=q))  == O[m]) for m in range(n_C))
# P1.addConstrs((O[m] <= Cmax for m in range(n_C)))

P1.optimize()
print("z* = ", P1.ObjVal)