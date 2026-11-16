from flask import Flask, render_template, request, redirect, url_for, flash, session

app = Flask(__name__)
app.secret_key = "412351453dbcgahytve3825" 

import os
import time

import stata_setup
stata_setup.config("/usr/local/stata18/", "se")
from pystata import stata

import plotly.express as px
import plotly.io as pio

import pandas as pd


user_id = 101

DP_pop = 0
DP_age_lb = 0
DP_age_ub = 100
DP_RRR = 10

DC_pop = 0
DC_age_lb = 0
DC_age_ub = 100
DC_HF_RRR = 10
DC_CV_RRR = 10
DC_CK_RRR = 10
DC_PN_RRR = 10

FC_PP = ""
FC_T = 100000
AC_PP = ""
AC_T = 100000

if DP_pop == "":
    DP_pop = "."
else:
    DP_pop = int(DP_pop)

if DP_age_lb == "":
    DP_age_lb = int(0)
else:
    DP_age_lb = int(DP_age_lb)

if DP_age_ub =="":
    DP_age_ub = int(100)
else:
    DP_age_ub = int(DP_age_ub)

if DP_RRR == "":
    DP_RRR = int(0)
else:
    DP_RRR = float(DP_RRR)/100

if DC_pop == "":
    DC_pop = "."
else:
    DC_pop = int(DC_pop)

if DC_age_lb =="":
    DC_age_lb = int(0)
else:
    DC_age_lb = int(DC_age_lb)

if DC_age_ub =="":
    DC_age_ub = int(100)
else:
    DC_age_ub = int(DC_age_ub)

if DC_HF_RRR == "":
    DC_HF_RRR = int(0)
else:
    DC_HF_RRR = float(DC_HF_RRR)/100

if DC_CV_RRR == "":
    DC_CV_RRR = int(0)
else:
    DC_CV_RRR = float(DC_CV_RRR)/100

if DC_CK_RRR == "":
    DC_CK_RRR = int(0)
else:
    DC_CK_RRR = float(DC_CK_RRR)/100

if DC_PN_RRR == "":
    DC_PN_RRR = int(0)
else:
    DC_PN_RRR = float(DC_PN_RRR)/100

if FC_PP == "":
    FC_PP = int(0)
else:
    FC_PP = float(FC_PP)

if FC_T == "":
    FC_T = int(0)
else:
    FC_T = float(FC_T)

if AC_PP == "":
    AC_PP = int(0)
else:
    AC_PP = float(AC_PP)

if AC_T == "":
    AC_T = int(0)
else:
    AC_T = float(AC_T)

#    image_filename = f"graph_{user_id}_u.svg"
#    image_path = os.path.join(app.root_path, 'static', image_filename)


stata.run('do stata_files/ALLSPARK.do')
stata.run(f'allspark {DP_pop} {DP_age_lb} {DP_age_ub} {DP_RRR} {DC_pop} {DC_age_lb} {DC_age_ub} {DC_HF_RRR} {DC_CV_RRR} {DC_CK_RRR} {DC_PN_RRR} {FC_PP} {FC_T} {AC_PP} {AC_T}')
stata.run('mat l r(resmat)')


#    session['current_graph'] = image_filename

result_mat = [stata.get_return()['r(resmat)']]
result_mat = result_mat[0].tolist()

for i in range(1,4):
    for j in range(0,9):
        result_mat[j][i] = round(result_mat[j][i],0)

result_mat[0][0] = 'Incident diabetes'
result_mat[1][0] = 'HF events'
result_mat[2][0] = 'CVD events'
result_mat[3][0] = 'CKD events'
result_mat[4][0] = 'PN events'
result_mat[5][0] = 'Deaths'
result_mat[6][0] = 'QALYs'
result_mat[7][0] = 'Healthcare costs (AUD)'
result_mat[8][0] = 'ICER'
result_mat[8][1] = ''
result_mat[8][2] = ''

print(result_mat)

QLY = result_mat[6][3]
HCC = result_mat[7][3]
data = [
    {"QLY": QLY, "HCC": HCC}
]

df = pd.DataFrame(data)

fig = px.scatter(df, 
                x="QLY", 
                y="HCC", 
                hover_data=['QLY','HCC'],
                title="Cost-effectiveness plane",
                )

fig.update_layout(
                xaxis_title="QALYs gained",
                yaxis_title="Incremental healthcare costs",
                font=dict(family="Courier New, monospace", size=18)
) 

minQLY = df['QLY'].min()-1000
xrangelb = min(minQLY,-2000)
maxQLY = df['QLY'].max()+1000
xrangeub = max(maxQLY,6000)

minHCC = df['HCC'].min()-20000
yrangelb = min(minHCC,-20000)
maxHCC = df['HCC'].max()+20000
yrangeub = max(maxHCC,200000)

fig.update_xaxes(
    range=[xrangelb, xrangeub],
    tickformat=',d'
    )
fig.update_yaxes(
    range=[yrangelb, yrangeub],
    tickformat='$,.2f'
    )

user_inputs = [DP_pop,DP_age_lb,DP_age_ub,DP_RRR,DC_pop,DC_age_lb,DC_age_ub,DC_HF_RRR,DC_CV_RRR,DC_CK_RRR,DC_PN_RRR,FC_PP,FC_T,AC_PP,AC_T]

print(user_inputs[2])

print(user_inputs)

print(len(user_inputs))
if len(user_inputs)!=15:
    print("WHOOPS")

rml = ["rm1","rm2"]
for rm in rml:
    print(rm)

#fig.show()

