import json
import sys
import itertools
import poek as pk

## Grab instance file from first command line argument
data_file = sys.argv[1]

print('loading data')
data = json.load(open(data_file, 'r'))

thermal_gens = data['thermal_generators']
renewable_gens = data['renewable_generators']

time_periods = {t+1 : t for t in range(data['time_periods'])}

gen_startup_categories = {g : list(range(0, len(gen['startup']))) for (g, gen) in thermal_gens.items()}
gen_pwl_points = {g : list(range(0, len(gen['piecewise_production']))) for (g, gen) in thermal_gens.items()}

print('building model')
m = pk.model()

S1 = list(itertools.product(thermal_gens.keys(), time_periods.keys()))
S2 = list(itertools.product(renewable_gens.keys(), time_periods.keys()))

cg = m.variable(index=S1)
pg = m.variable(index=S1, lb=0)  
rg = m.variable(index=S1, lb=0)  
pw = m.variable(index=S2, lb=0)
ug = m.variable(index=S1, binary=True) 
vg = m.variable(index=S1, binary=True) 
wg = m.variable(index=S1, binary=True) 

dg = m.variable(index=list((g,s,t) for g in thermal_gens for s in gen_startup_categories[g] for t in time_periods), binary=True) ##
lg = m.variable(index=list((g,l,t) for g in thermal_gens for l in gen_pwl_points[g] for t in time_periods), lb=0, ub=1) ##

# obj =
m.add( sum(
                          sum(
                              cg[g,t] + gen['piecewise_production'][0]['cost']*ug[g,t]
                              + sum( gen_startup['cost']*dg[g,s,t] for (s, gen_startup) in enumerate(gen['startup']))
                          for t in time_periods)
                        for g, gen in thermal_gens.items() )
                        ) #(1)

#demand = Constraint(time_periods.keys())
#reserves = Constraint(time_periods.keys())
for t,t_idx in time_periods.items():
    #demand[t] = 
    m.add( sum( pg[g,t]+gen['power_output_minimum']*ug[g,t] for (g, gen) in thermal_gens.items() ) + sum( pw[w,t] for w in renewable_gens ) == data['demand'][t_idx] ) #(2) 
    #reserves[t] = 
    m.add( sum( rg[g,t] for g in thermal_gens ) >= data['reserves'][t_idx] ) #(3)

#uptimet0 = Constraint(thermal_gens.keys())
#downtimet0 = Constraint(thermal_gens.keys())
#logicalt0 = Constraint(thermal_gens.keys())
#startupt0 = Constraint(thermal_gens.keys())

#rampupt0 = Constraint(thermal_gens.keys())
#rampdownt0 = Constraint(thermal_gens.keys())
#shutdownt0 = Constraint(thermal_gens.keys())

for g, gen in thermal_gens.items():
    if gen['unit_on_t0'] == 1:
        if gen['time_up_minimum'] - gen['time_up_t0'] >= 1:
            #uptimet0[g] =
            m.add( sum( (ug[g,t] - 1) for t in range(1, min(gen['time_up_minimum'] - gen['time_up_t0'], data['time_periods'])+1)) == 0 ) #(4)
    elif gen['unit_on_t0'] == 0:
        if gen['time_down_minimum'] - gen['time_down_t0'] >= 1:
            #downtimet0[g] =
            m.add( sum( ug[g,t] for t in range(1, min(gen['time_down_minimum'] - gen['time_down_t0'], data['time_periods'])+1)) == 0 ) #(5)
    else:
        raise Exception('Invalid unit_on_t0 for generator {}, unit_on_t0={}'.format(g, gen['unit_on_t0']))

    #logicalt0[g] =
    m.add( ug[g,1] - gen['unit_on_t0'] == vg[g,1] - wg[g,1] ) #(6)

    startup_expr = sum( 
                        sum( dg[g,s,t] 
                                for t in range(
                                                max(1,gen['startup'][s+1]['lag']-gen['time_down_t0']+1),
                                                min(gen['startup'][s+1]['lag']-1,data['time_periods'])+1
                                              )
                            ) 
                       for s,_ in enumerate(gen['startup'][:-1])) ## all but last
    if isinstance(startup_expr, int):
        pass
    else:
        #startupt0[g] =
        m.add( startup_expr == 0 ) #(7)

    #rampupt0[g] =
    m.add( pg[g,1] + rg[g,1] - gen['unit_on_t0']*(gen['power_output_t0']-gen['power_output_minimum']) <= gen['ramp_up_limit'] ) #(8)

    #rampdownt0[g] =
    m.add( gen['unit_on_t0']*(gen['power_output_t0']-gen['power_output_minimum']) - pg[g,1] <= gen['ramp_down_limit'] ) #(9)


    shutdown_constr = gen['unit_on_t0']*(gen['power_output_t0']-gen['power_output_minimum']) <= gen['unit_on_t0']*(gen['power_output_maximum'] - gen['power_output_minimum']) - max((gen['power_output_maximum'] - gen['ramp_shutdown_limit']),0)*wg[g,1] #(10)

    if isinstance(shutdown_constr, bool):
        pass
    else:
        #shutdownt0[g] =
        m.add( shutdown_constr )

#mustrun = Constraint(thermal_gens.keys(), time_periods.keys())
#logical = Constraint(thermal_gens.keys(), time_periods.keys())
#uptime = Constraint(thermal_gens.keys(), time_periods.keys())
#downtime = Constraint(thermal_gens.keys(), time_periods.keys())
#startup_select = Constraint(thermal_gens.keys(), time_periods.keys())
#gen_limit1 = Constraint(thermal_gens.keys(), time_periods.keys())
#gen_limit2 = Constraint(thermal_gens.keys(), time_periods.keys())
#ramp_up = Constraint(thermal_gens.keys(), time_periods.keys())
#ramp_down = Constraint(thermal_gens.keys(), time_periods.keys())
#power_select = Constraint(thermal_gens.keys(), time_periods.keys())
#cost_select = Constraint(thermal_gens.keys(), time_periods.keys())
#on_select = Constraint(thermal_gens.keys(), time_periods.keys())

for g, gen in thermal_gens.items():
    for t in time_periods:
        #mustrun[g,t] =
        m.add( ug[g,t] >= gen['must_run'] ) #(11)

        if t > 1:
            #logical[g,t] =
            m.add( ug[g,t] - ug[g,t-1] == vg[g,t] - wg[g,t] ) #(12)

        UT = min(gen['time_up_minimum'],data['time_periods'])
        if t >= UT:
            #uptime[g,t] =
            m.add( sum(vg[g,t] for t in range(t-UT+1, t+1)) <= ug[g,t] ) #(13)
        DT = min(gen['time_down_minimum'],data['time_periods'])
        if t >= DT:
            #downtime[g,t] =
            m.add( sum(wg[g,t] for t in range(t-DT+1, t+1)) <= 1-ug[g,t] ) #(14)
        #startup_select[g,t] =
        m.add( vg[g,t] == sum(dg[g,s,t] for s,_ in enumerate(gen['startup'])) ) #(16)

        #gen_limit1[g,t] =
        m.add( pg[g,t]+rg[g,t] <= (gen['power_output_maximum'] - gen['power_output_minimum'])*ug[g,t] - max((gen['power_output_maximum'] - gen['ramp_startup_limit']),0)*vg[g,t] ) #(17)

        if t < len(time_periods): 
            #gen_limit2[g,t] =
            m.add( pg[g,t]+rg[g,t] <= (gen['power_output_maximum'] - gen['power_output_minimum'])*ug[g,t] - max((gen['power_output_maximum'] - gen['ramp_shutdown_limit']),0)*wg[g,t+1] ) #(18)

        if t > 1:
            #ramp_up[g,t] =
            m.add( pg[g,t]+rg[g,t] - pg[g,t-1] <= gen['ramp_up_limit'] ) #(19)
            #ramp_down[g,t] =
            m.add( pg[g,t-1] - pg[g,t] <= gen['ramp_down_limit'] ) #(20)

        piece_mw1 = gen['piecewise_production'][0]['mw']
        piece_cost1 = gen['piecewise_production'][0]['cost']
        #power_select[g,t] =
        m.add( pg[g,t] == sum( (piece['mw'] - piece_mw1)*lg[g,l,t] for l,piece in enumerate(gen['piecewise_production'])) ) #(21)
        #cost_select[g,t] =
        m.add( cg[g,t] == sum( (piece['cost'] - piece_cost1)*lg[g,l,t] for l,piece in enumerate(gen['piecewise_production'])) ) #(22)
        #on_select[g,t] =
        m.add( ug[g,t] == sum(lg[g,l,t] for l,_ in enumerate(gen['piecewise_production'])) ) #(23)

#startup_allowed = Constraint(dg_index)
for g, gen in thermal_gens.items():
    for s,_ in enumerate(gen['startup'][:-1]): ## all but last
        for t in time_periods:
            if t >= gen['startup'][s+1]['lag']:
                #startup_allowed[g,s,t] =
                m.add( dg[g,s,t] <= sum(wg[g,t-i] for i in range(gen['startup'][s]['lag'], gen['startup'][s+1]['lag'])) ) #(15)

for w, gen in renewable_gens.items():
    for t, t_idx in time_periods.items():
        pw[w,t].lb = gen['power_output_minimum'][t_idx] #(24)
        pw[w,t].ub = gen['power_output_maximum'][t_idx] #(24)

print("model setup complete")

m.write("poek.lp")
sys.exit(0)

if False:
    from pyomo.opt import SolverFactory
    cbc = SolverFactory('cbc')

    print("solving")
    cbc.solve(m, options={'ratioGap':0.01}, tee=True)

