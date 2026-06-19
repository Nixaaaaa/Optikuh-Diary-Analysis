# Speaker Notes - OptiKuh EDA

Use this as a quick script. Keep the focus on EDA and avoid promising a model in your part.

## Slide 1 - Title
"I will start with the exploratory data analysis setup for the OptiKuh dataset. My part is only EDA: understanding the table, data coverage, missingness, and health/disease distributions."

## Slide 2 - Project context and scope
"The project is about using biomarkers and routine cow measurements for health monitoring. The dataset combines routine farm records, milk data, body condition variables, and laboratory biomarkers. For this presentation I am not building a risk model yet. I am checking whether the dataset is structured and understandable enough for later modeling."

## Slide 3 - VS Code workflow
"Because the original Excel file is large, I created a reproducible pipeline. First we convert it once into a CSV cache. Then the EDA script produces tables and figures. The LaTeX presentation reads those generated figures, so if we rerun the EDA, the slides can be updated quickly."

## Slide 4 - Dataset structure
"The main unit is a daily animal record. The file contains 492,540 daily records, 1,714 animals, 12 anonymized farms, and about 3,422 lactation episodes. The observation window runs from 2014-08-28 to 2017-03-23. This unit matters, because daily rows are repeated measurements from the same cows."

## Slide 5 - Health status distribution
"Health status is assigned per lactation, not per daily row. So I show the lactation episode distribution here. The largest group is healthy with 1,547 episodes. Production disease only has 404 episodes, and there are also mixed production plus other disease episodes. This tells us the target will be imbalanced if used later."

## Slide 6 - Farm and breed coverage
"Farms are anonymized from 1 to 12. The data coverage is not equal across farms, so farm effects could matter later. Breed is coded, but I keep the raw code labels until the official codebook is confirmed."

## Slide 7 - Missingness and availability
"The biomarker columns have high missingness, but this is expected because blood and urine samples were collected at selected time points, not daily. For EDA this is a design feature, not automatically a quality problem."

## Slide 8 - Time and lactation coverage
"The records cover a long observation window and a wide range of days in milk. This means any later analysis must decide the time window carefully, especially if predicting disease around calving."

## Slide 9 - Disease categories
"The disease labels are grouped into categories such as udder, claw, reproduction, metabolic, respiratory, digestive, parasitic, and other. The largest disease event category in daily rows is claw/hoof. I also show the top diagnosis labels to understand what is actually driving the categories."

## Slide 10 - Production diseases
"The project material defines production diseases such as mastitis, metritis, retained placenta, cycle disorders, hypocalcemia, ketosis, and displaced abomasum. For EDA we count them first. For modeling later, we must avoid leakage by using only predictors available before the outcome."

## Slide 11 - Milk and biomarker profiles
"These boxplots are exploratory. They show whether central distributions differ across health groups, but they do not prove causality. The full summaries are saved in the output tables."

## Slide 12 - Correlations
"This heatmap is just a quick overview of relationships among selected numeric variables. Because there are repeated cow-level rows and different sampling frequencies, correlations should be treated as descriptive only."

## Slide 13 - Takeaways
"The project setup is ready: reproducible conversion, EDA script, tables, figures, and LaTeX slides. The key EDA message is that the dataset is rich but hierarchical. Daily records are nested in cows and lactation episodes, and different variables have different measurement frequencies. That structure must be respected in any next modeling step."
