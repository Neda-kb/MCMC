import numpy as np
import pandas as pd
import pymc as pm
from multiprocessing import Pool
import arviz as az

# Load data
data = pd.read_csv('bank-full.csv' ,delimiter=';')

# Convert categorical variables to numeric
data['job'] = data['job'].astype('category').cat.codes
data['marital'] = data['marital'].astype('category').cat.codes
data['education'] = data['education'].astype('category').cat.codes

X = data[['age', 'job', 'marital', 'education']]
# Convert 'yes'/'no' to 1/0
y = data['y'].apply(lambda x: 1 if x == 'yes' else 0)

# Group by job type and education level
data['group_idx'] = data['job']
n_groups = data['group_idx'].nunique()

with pm.Model() as hierarchical_model:
    # Hyperpriors for group nodes
    mu_a = pm.Normal('mu_a', mu=0., sigma=10)
    sigma_a = pm.HalfCauchy('sigma_a', beta=5)

    # Varying intercepts for each group
    a = pm.Normal('a', mu=mu_a, sigma=sigma_a, shape=n_groups)

    # Linear coefficients for predictors
    beta = pm.Normal('beta', mu=0., sigma=10, shape=X.shape[1])

    # Model error
    eps = pm.HalfCauchy('eps', beta=5)

    # Expected value
    y_est = a[data['group_idx']] + pm.math.dot(X, beta)

    # Likelihood
    y_like = pm.Normal('y_like', mu=y_est, sigma=eps, observed=y)

    # Sampling from the posterior
    trace = pm.sample(1000, return_inferencedata=True)

with hierarchical_model:
    trace = pm.sample(1000, return_inferencedata=True)

# Trace plot to diagnose MCMC convergence
az.plot_trace(trace)
az.plot_posterior(trace)
az.summary(trace)
az.plot_pair(trace, kind='kde')
az.plot_energy(trace)

def run_mcmc_on_shard(shard, num_samples=10, num_tune=20):
    shard_sample = shard.sample(frac=0.10)
    with pm.Model() as shard_model:
        # Define your model here using shard_sample
        step = pm.Metropolis()
        trace = pm.sample(num_samples, tune=num_tune, step=step, cores=1, return_inferencedata=False)
    return trace

# Use 10% of data, split into 2 shards
shards = np.array_split(data.sample(frac=0.10), 2)

# Run MCMC on shards with 2 processes
with Pool(processes=2) as pool:
    shard_traces = pool.map(run_mcmc_on_shard, shards)

# Combine traces from all shards
combined_trace = pm.backends.base.merge_traces(shard_traces)


az.plot_trace(combined_trace)
summary = az.summary(combined_trace)
print(summary)