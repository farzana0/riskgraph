"""Plot the recorded framework comparison; requires requirements-simulation.txt."""
import argparse
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',default='docs/examples/framework-v2.json')
    parser.add_argument('--output',default='docs/images/framework-v2.png')
    args=parser.parse_args()
    data=json.loads(Path(args.input).read_text())
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,
                         'figure.facecolor':'#fafbf7','axes.facecolor':'#fafbf7'})
    fig,axes=plt.subplots(1,2,figsize=(13,5.7))
    colors={'v1':'#bea483','v2':'#216b5b'}
    selected=[row for row in data['alarms'] if row['scenario'] in ['moderate_012','moderate_015','moderate_020','large_025']]
    positions=np.arange(len(selected))
    for index,version in enumerate(['v1','v2']):
        stats=[row['versions'][version]['crossing_by_horizon']['500'] for row in selected]
        values=np.array([stat['rate']*100 for stat in stats])
        ci=np.array([stat['ci95'] for stat in stats])*100
        xs=positions+(index-.5)*.34
        axes[0].bar(xs,values,.34,color=colors[version],label='Original alarm' if version=='v1' else 'Mixture alarm',
                    yerr=np.array([values-ci[:,0],ci[:,1]-values]),capsize=3)
        for group,(x,value) in enumerate(zip(xs,values)):
            other=selected[group]['versions']['v1' if version=='v2' else 'v2']['crossing_by_horizon']['500']['rate']*100
            offset=13 if version=='v2' and abs(value-other)<10 else 4
            label='100%' if value==100 else f'{value:.2f}%' if value>99.9 else f'{value:.1f}%'
            axes[0].text(x,value+offset,label,ha='center',fontsize=9,fontweight='bold')
    axes[0].set_xticks(positions,['12%','15%','20%','25%'])
    axes[0].set_ylim(0,125)
    axes[0].set_ylabel('Runs that trigger within 500 decisions (%)')
    axes[0].set_xlabel('True harmful-proposal probability')
    axes[0].set_title('Stronger sensitivity to moderate harm',loc='left',fontweight='bold',pad=15)
    axes[0].legend(frameon=False,loc='upper left',fontsize=9)
    rows=data['zero_loss_bounds']
    for version in ['v1','v2']:
        axes[1].plot([row['n'] for row in rows],[row[f'{version}_upper_usd'] for row in rows],
                     marker='o',color=colors[version],label='Hoeffding reference' if version=='v1' else 'Tail confidence sequence',lw=2)
    axes[1].set_xscale('log')
    axes[1].set_xticks([3,10,20,40,100,200,500],['3','10','20','40','100','200','500'])
    axes[1].set_xlabel('Zero-loss decisions observed')
    axes[1].set_ylabel('Upper bound on mean loss (USD / decision)')
    axes[1].set_title('Tighter upper bounds under stated assumptions',loc='left',fontweight='bold',pad=15)
    axes[1].legend(frameon=False,fontsize=9)
    fig.suptitle('RiskGraph · Framework comparison',x=.07,y=.98,ha='left',fontsize=20,fontweight='bold')
    fig.text(.07,.88,'Paired synthetic trajectories; methods and scenario definitions fixed before the recorded comparison.',fontsize=10,color='#5c6c54')
    fig.subplots_adjust(left=.075,right=.98,top=.76,bottom=.22,wspace=.32)
    null=next(row for row in data['alarms'] if row['scenario']=='null_010')
    false=null['versions']['v2']['crossing_by_horizon']['500']['rate']*100
    fig.text(.075,.095,f'Alarm: {selected[0]["trajectories"]:,} trajectories per scenario; 95% Monte Carlo error bars. Null false alarms: {false:.2f}% (5% budget).',fontsize=9,color='#53664b')
    fig.text(.075,.05,'Bounds: 2.5% error per stream; fixed conditional tail probabilities and $1,000 cap. Synthetic results do not establish production safety.',fontsize=9,color='#53664b')
    target=Path(args.output);target.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(target,dpi=170);plt.close(fig)
    print(target)


if __name__=='__main__':main()
