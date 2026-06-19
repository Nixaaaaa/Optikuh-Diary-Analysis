# OptiKuh EDA summary

## Data structure
- Daily records: 492,540
- Variables: 49
- Animals: 1,714
- Farms: 12
- Approx. lactation episodes: 3,086
- Observation window: 2014-08-28 to 2017-03-23

## Health status by lactation episode
- Healthy: 1,234 (39.97%)
- Production disease: 402 (13.02%)
- Other disease: 721 (23.36%)
- Production + other disease: 730 (23.65%)

## Main disease categories by daily event rows
- Claw/hoof (kl): 1,284 rows, 1,000 episodes
- Reproduction (fr): 839 rows, 658 episodes
- Udder (eu): 605 rows, 581 episodes
- Parasitic (pa): 562 rows, 554 episodes
- Metabolic (st): 423 rows, 353 episodes
- Other (so): 192 rows, 168 episodes
- Digestive (vo): 53 rows, 53 episodes
- Respiratory (at): 25 rows, 24 episodes

## Highest missingness
- vo: 99.99% missing
- at: 99.99% missing
- so: 99.96% missing
- st: 99.91% missing
- pa: 99.89% missing
- eu: 99.88% missing
- fr: 99.83% missing
- kl: 99.74% missing
- nsba: 99.51% missing
- insulin: 98.57% missing

## Speaking focus
- This is a longitudinal daily dataset, but the outcome status is defined at lactation level.
- Biomarker variables are sparse by design because blood/urine samples were collected on specific days.
- No modelling is done here; all results are descriptive EDA.