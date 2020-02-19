"""Contains a set of misc. useful tools for the compressive learning toolbox"""

import numpy as np
from scipy.stats import multivariate_normal
import matplotlib.pyplot as plt

############################
# DATASET GENERATION TOOLS #
############################

def generatedataset_GMM(d,K,n,output_required='dataset',balanced=True,normalize=None,**generation_params):
    """
    Generate a synthetic dataset according to a Gaussian Mixture Model distribution.
    
    Parameters
    ----------
    d: int, the dataset dimension
    K: int, the number of Gaussian modes
    n: int, the number of elements in the dataset (cardinality)
    output_required: string (default='dataset'), specifies the required outputs (see below). Available options:
       - 'dataset': returns X, the dataset;
       - 'GMM': returns (X,GMM), where GMM = (weigths,means,covariances) is a tuple describing the generating mixture;
       - 'labels': returns (X,y), the dataset and the associated labels (e.g., for classification)
       - 'all': returns (X,y,GMM)
    balanced:  - bool (default=True), if True the Gaussians have the same weights, or
               - real (must be > 0.), stength of weight imbalance (~0 is very imbalanced, > K is fairly balanced)
    normalize: string (default=None), if not None describes how to normalize the dataset. Available options:
            - 'l_2-unit-ball': the dataset is scaled in the l_2 unit ball (i.e., all l_2 norms are <= 1)
            - 'l_inf-unit-ball': the dataset is projected in the l_inf unit ball (i.e., all entries are <= 1)
    
        
    Returns
    -------
    out: array-like or tuple, a combination of the following items (see desciption of output_required):
        - X: (n,d)-numpy array containing the samples; only output by default
        - weigths:     (K,)-numpy array containing the weigthing factors of the Gaussians
        - means:       (K,d)-numpy array containing the means of the Gaussians
        - covariances: (K,d,d)-numpy array containing the covariance matrices of the Gaussians
        - y: (n,)-numpy array containing the labels (from 0 to K, one per mode) associated with the items in X
    
    
    Other Parameters
    ----------------
    TODO UPDATE THIS
    isotropic: bool (default=True), if True each Gaussian has covariance of type scalar*Identity
    
    """
    ## STEP 0: Parse input generation parameters
    # Default generation parameters
    _gen_params = {
        'separation_scale': (10/np.sqrt(d)), # Separation of the Gaussians
        'separation_min': 0, # Before norm
        'covariance_variability_inter': 8., # between clusters
        'covariance_variability_intra': 3., # inside one mode 
        'all_covariance_scaling': 0.1} 
    # Check the inputs, if it's a valid parameter overwrite it in the internal parameters dict "_gen_params"
    for param_name in generation_params:
        if param_name in _gen_params.keys():
            _gen_params[param_name] = generation_params[param_name]
        else:
            raise ValueError('Unrecognized parameter: {}'.format(param_name))
    if _gen_params['separation_min'] > 2 * _gen_params['separation_scale']:
        print("WARNING: minimum separation too close to typical separation scale, finding separated clusters might be hard")
    
    ## STEP 1: generate the weights of the Gaussian modes
    # Convert input to a "randomness strength"
    if isinstance(balanced,bool):
        weight_perturbation_strength = 0. if balanced else 3.
    else:
        weight_perturbation_strength = 1./balanced
    # Generate random weigths, normalize
    weights = np.ones(K) + weight_perturbation_strength*np.random.rand(K) 
    weights /= np.sum(weights)
    # Avoid almost empty classes
    minweight = min(0.005,(K-1)/(n-1)) # Some minimum weight to avoid empty classes
    weights[np.where(weights < minweight)[0]] = minweight
    
    ## STEP 2: Draw the assignations of each of the vectors to assign
    y = np.random.choice(K,n,p=weights)
    
    ## STEP 3: Fill the dataset
    # Pre-allocate memory
    X = np.empty((n,d))
    means = np.empty((K,d))
    covariances = np.empty((K,d,d))
    
    # Loop over the modes and generate each Gaussian
    for k in range(K):
        
        # Generate mean for this mode
        successful_mu_generation = False
        while not successful_mu_generation:
            
            mu_this_mode = _gen_params['separation_scale']*np.random.randn(d)
            if k == 0 or _gen_params['separation_min'] == 0:
                successful_mu_generation = True
            else:
                distance_to_closest_mode = min(np.linalg.norm(mu_this_mode - mu_other) for mu_other in means[:k])
                successful_mu_generation = distance_to_closest_mode > _gen_params['separation_min']
        # Generate covariance for this mode
        scale_variance_this_mode = 1. + np.random.uniform(0,_gen_params['covariance_variability_inter'])
        scale_variance_this_mode *= _gen_params['all_covariance_scaling'] # take into account global scaling
        unscaled_variances_this_mode = np.ones(d) + np.random.uniform(0,_gen_params['covariance_variability_intra'],d) 
        Sigma_this_mode = scale_variance_this_mode*np.diag(unscaled_variances_this_mode)
        
        # Save the mean and covariance
        means[k] = mu_this_mode
        covariances[k] = Sigma_this_mode
        
        # Get the indices we have to fill
        indices_for_this_mode = np.where(y == k)[0]
        nb_samples_in_this_mode = indices_for_this_mode.size
        
        # Fill the dataset with samples drawn from the current mode

        X[indices_for_this_mode] = np.random.multivariate_normal(mu_this_mode, Sigma_this_mode, nb_samples_in_this_mode)
        
        
    ## STEP 4: If needed, normalize the dataset
    if normalize is not None:
        if normalize in ['l_2-unit-ball']:
            maxNorm = np.linalg.norm(X,axis=1).max() + 1e-6 # plus smth to have 
        elif normalize in ['l_inf-unit-ball']:
            maxNorm = np.abs(X).max() + 1e-6
        else:
            raise Exception('Unreckognized normalization method ({}). Aborting.'.format(normalize))
        # Normalize by maxNorm
        X /= maxNorm
        means /= maxNorm
        covariances /= maxNorm**2
    
    ## STEP 5: output
    if output_required == 'dataset':
        out = X
    elif output_required == 'GMM':
        out = (X,(weights,means,covariances))
    elif output_required == 'labels':
        out = (X,y)
    elif output_required == 'all':
        out = (X,y,(weights,means,covariances))
    else:
        raise ValueError('Unrecognized output_required ({})'.format(output_required))
    return out




def generateCirclesDataset(K,n,normalize):
    """
    Generate a synthetic 2-D dataset comprising concentric circles/shells.
    
    Parameters
    ----------
    K: int, the number of circles modes
    n: int, the number of elements in the dataset (cardinality)
    normalize: string (default=None), if not None describes how to normalize the dataset. Available options:
            - 'l_2-unit-ball': the dataset is scaled in the l_2 unit ball (i.e., all l_2 norms are <= 1)
            - 'l_inf-unit-ball': the dataset is projected in the l_inf unit ball (i.e., all entries are <= 1)
    
        
    Returns
    -------
    out:  X: (n,d)-numpy array containing the samples.
    """
    weigths = np.ones(K)/K  # True, ideal weigths (balanced case)
    classSizes = np.ones(K) # Actual samples per class
    # (note: we enforce that weigths is the *actual* proportions in this dataset)
    
    ## Select number of samples of each mode
    balanced = True # FOR NOW,TODO CHANGE LATER
    if balanced:
        classSizes[:-1] = int(n/K)
        classSizes[-1] = n - (K-1)*int(n/K) # ensure we have exactly n samples in dataset even if n % K != 0
    else:
        minweight = min(0.01,(K-1)/(n-1)) # Some minimum weight to avoid empty classes
        weigths = np.random.uniform(minweight,1,K) 
        weigths = weigths/np.sum(weigths) # Normalize
        classSizes[:-1] = (weigths[:-1]*n).astype(int)
        classSizes[-1] = n - np.sum(classSizes[:-1])
    classSizes = classSizes.astype(int)

    ## Initialization
    X = None
    
    ## Some internal params (TODO allow to give them as optional args? kind of arbitrary!)
    #scale_separation = (5/np.sqrt(d)) # Separation of the Gaussians
    #scale_variance_b = np.array([0.05,0.95])/np.sqrt(d) # Bounds on the scale variance (actually, SD)
    
    ## Add each mode one by one 
    for k in range(K):
        classN = classSizes[k]
        #mu = scale_separation*np.random.randn(d) 
        #scale_variance = np.random.uniform(scale_variance_b[0],scale_variance_b[1])
        R = 1+3*np.random.randn(1) # mean
        Rs = R + 0.08*np.random.randn(classN)
        thetas = np.random.uniform(0,2*np.pi,classN)
        x1 = np.expand_dims(np.cos(thetas)*Rs,axis=1)
        x2 = np.expand_dims(np.sin(thetas)*Rs,axis=1)
        
        newCluster = np.concatenate((x1,x2),axis=1)
        if X is None:
            X = newCluster
        else:
            X = np.append(X,newCluster,axis=0)
            
    if normalize is not None:
        if normalize in ['l_2-unit-ball']:
            maxNorm = np.linalg.norm(X,axis=1).max() + 1e-6 # plus smth to have 
        elif normalize in ['l_inf-unit-ball']:
            maxNorm = np.abs(X).max() + 1e-6
        else:
            raise Exception('Unreckognized normalization method ({}). Aborting.'.format(normalize))
        # Normalize by maxNorm
        X /= maxNorm
            
    return X


def generateSpiralDataset(n,normalize=None,return_density=False):
    """
    Generate a synthetic 2-D dataset made of a spiral.
    
    Parameters
    ----------
    n: int, the number of elements in the dataset (cardinality)
    normalize: string (default=None), if not None describes how to normalize the dataset. Available options:
            - 'l_2-unit-ball': the dataset is scaled in the l_2 unit ball (i.e., all l_2 norms are <= 1)
            - 'l_inf-unit-ball': the dataset is projected in the l_inf unit ball (i.e., all entries are <= 1)
    
        
    Returns
    -------
    out:  X: (n,d)-numpy array containing the samples.
    """

    ## Initialization
    X = None
    
    # Spiral parameters
    n_spirals = 1
    min_radius = 0.3
    delta_radius_per_spiral = 1.2
    radius_noise =  0.01
    
    # parameter
    t = np.random.uniform(0,n_spirals,n)
    
    Rs = min_radius + delta_radius_per_spiral*t + radius_noise*np.random.randn(n)
    thetas = np.remainder(2*np.pi*t,2*np.pi)
    x1 = np.expand_dims(np.cos(thetas)*Rs,axis=1)
    x2 = np.expand_dims(np.sin(thetas)*Rs,axis=1)

    X = np.concatenate((x1,x2),axis=1)
            
        
    maxNorm = 1
    if normalize is not None:
        if normalize in ['l_2-unit-ball']:
            maxNorm = np.linalg.norm(X,axis=1).max() + 1e-6 # plus smth to have no round error
        elif normalize in ['l_inf-unit-ball']:
            maxNorm = np.abs(X).max() + 1e-6
        else:
            raise Exception('Unreckognized normalization method ({}). Aborting.'.format(normalize))
        # Normalize by maxNorm
        X /= maxNorm
     
    # Compute the density function too
    def pdf(x):
        # Compute polar coordinates TODO SUPPORT FOR N SPIRALS > 1
        x1 = x[0] * maxNorm
        x2 = x[1] * maxNorm
        r = np.sqrt(x1**2+x2**2)
        th = np.arctan2(x2,x1)
        if th<0:
            th += 2*np.pi
        return (1/(2*np.pi)) * (scipy.stats.norm.pdf(r, loc=min_radius + delta_radius_per_spiral*th/(2*np.pi), scale=radius_noise)) / r # First part comes from theta, second from R
        
    if return_density:        
        return (X,pdf)
    return X






############################
#         METHODS          #
############################

def EM_GMM(X,K,max_iter = 20):
    """Usual Expectation-Maximization (EM) algorithm for fitting mixture of Gaussian models (GMM).
    
    Arguments:
        - X: (n,d)-numpy array, the dataset of n examples in dimension d
        - K: int, the number of Gaussian modes
        - max_iter: int, the number of EM iterations to perform
        
    Returns: a tuple (w,mus,Sigmas) of three numpy arrays
        - w:      (K,)   -numpy array containing the weigths ('mixing coefficients') of the Gaussians
        - mus:    (K,d)  -numpy array containing the means of the Gaussians
        - Sigmas: (K,d,d)-numpy array containing the covariance matrices of the Gaussians
    """
    # TODO to improve:
    # - detect early convergence
    
    # Parse input
    (n,d) = X.shape
    lowb = np.amin(X,axis=0)
    uppb = np.amax(X,axis=0)
    
    # Initializations
    w = np.ones(K)
    mus = np.empty((K,d))
    Sigmas = np.empty((K,d,d)) # Covariances are initialized as random diagonal covariances, with folded Gaussian values
    for k in range(K):
        mus[k] = np.random.uniform(lowb,uppb)
        Sigmas[k] = np.diag(np.abs(np.random.randn(d)))
    r = np.empty((n,K)) # Matrix of posterior probabilities, here memory allocation only

    # Main loop
    for i in range(max_iter):
        # E step
        for k in range(K):
            r[:,k] = w[k]*multivariate_normal.pdf(X, mean=mus[k], cov=Sigmas[k],allow_singular=True)
        r = (r.T/np.sum(r,axis=1)).T # Normalize (the posterior probabilities sum to 1). Dirty :-(

        # M step: 1) update w
        w = np.sum(r,axis=0)/n 

        # M step: 2) update centers
        for k in range(K):
            mus[k] = r[:,k]@X/np.sum(r[:,k])

        # M step: 3) update Sigmas
        for k in range(K):
            # Dumb implementation
            num = np.zeros((d,d))
            for i in range(n):
                num += r[i,k]*np.outer(X[i]-mus[k],X[i]-mus[k])
            Sigmas[k] = num/np.sum(r[:,k])

        # (end of one EM iteration)
    return (w,mus,Sigmas)


############################
#         METRICS          #
############################


def SSE(X,C):
    """Computes the Sum of Squared Errors of some centroids on a dataset, given by
        SSE(X,C) = sum_{x_i in X} min_{c_k in C} ||x_i-c_k||_2^2.
    
    Arguments:
        - X: (n,d)-numpy array, the dataset of n examples in dimension d
        - C: (K,d)-numpy array, the K centroids in dimension d
        
    Returns:
        - SSE: real, the SSE score defined above
    """
    # Dumb implementation of the SSE
    SSE = 0.
    for i in range(X.shape[0]):
        SSE += np.min(np.linalg.norm(C-X[i],axis=1))**2
    return SSE

def loglikelihood_GMM(P,X,robust = True):
    """Computes the loglikelihood of GMM model P on data X, defined as follows:
        loglikelihood = (1/n) * sum_{i=1..n} log(sum_{k=1..K} (w_k)*N(x_i ; mu_k, Sigma_k) )
    
    Arguments:
        - P: tuple of three numpy arrays describing the GMM model of form (w,mus,Sigmas)
            - w      : (K,)-numpy array, the weights of the K Gaussians (should sum to 1)
            - mus    : (K,d)-numpy array containing the means of the Gaussians
            - Sigmas : (K,d,d)-numpy array containing the covariance matrices of the Gaussians
        - X: (n,d)-numpy array, the dataset of n examples in dimension d
        - robust: bool (default = True), if True, avoids -inf output due to very small probabilities
                  (note: execution will be slower)
        
    Returns:
        - loglikelihood: real, the loglikelihood value defined above
    """
    
    # TODO : avoid recomputations of inv
    
    # Unpack
    (w,mu,Sig) = P
    (K,d) = mu.shape
    
    logp = np.zeros(X.shape[0])
    p = np.zeros(X.shape[0])
    
    for k in range(K):
        p += w[k]*multivariate_normal.pdf(X, mean=mu[k], cov=Sig[k], allow_singular=True)
    logp = np.log(p)
    
    if robust:
        b = np.zeros(K)
        a = np.zeros(K)
        for k in range(K):
            a[k] = w[k]*((2*np.pi)**(-d/2))*(np.linalg.det(Sig[k])**(-1/2))
        for i in np.where(p==0)[0]: # Replace the inf values due to rounding p to 0
            for k in range(K):
                b[k] = -(X[i]-mu[k])@np.linalg.inv(Sig[k])@(X[i]-mu[k])/2
            lc = b.max()
            ebc = np.exp(b-lc)
            logp[i] = np.log(ebc@a) + lc
        
        
    return np.mean(logp)


def symmKLdivergence_GMM(P1,P2,Neval = 500000,verbose=0):
    """Computes the symmetric KL divergence between two GMM densities."""
    tol = 1e-7
    # TODO : a version that adapts Neval s.t. convergence?
    # Unpack
    (w1,mu1,Sig1) = P1
    (w2,mu2,Sig2) = P2
    K1 = w1.size
    K2 = w2.size
    
    Neval # Number of samples to evaluate the KL divergence
    
    # dumb implem for now, TODO FAST IMPLEM!
    KLestimate = 0.
    for i in range(Neval):
        # Sample from P1
        index_gaussianDrawnFrom = np.random.choice(np.arange(K1),p=w1)
        y = np.random.multivariate_normal(mu1[index_gaussianDrawnFrom], Sig1[index_gaussianDrawnFrom])
        
        # Evaluate density of P1
        p1 = 0.
        for k in range(K1):
            p1 += w1[k]*multivariate_normal.pdf(y, mean=mu1[k], cov=Sig1[k], allow_singular=True)
        
        # Evaluate density of P2
        p2 = 0.
        for k in range(K2):
            p2 += w2[k]*multivariate_normal.pdf(y, mean=mu2[k], cov=Sig2[k], allow_singular=True)
        
        # Compute the contribution
        contribution_i = np.log(p1/p2) + (p2/p1)*np.log(p2/p1)
        if (p1 < tol) and (p2 < tol):
            contribution_i = 0. # Avoid rounding errors (?)
        
        # Add it
        KLestimate = KLestimate*(i/(i+1)) + contribution_i/(i+1)
        if i%10000 == 0:
            if verbose > 0: print(i,KLestimate)
            
        
        
    return KLestimate



############################
#      VISUALIZATION       #
############################
from matplotlib.patches import Ellipse
from scipy.stats import chi2

def plotGMM(X=None,P=None,dims=(0,1),d=2,proportionInGMM = None):
    """TODO"""
    # To finish

    if P is not None:
        (w,mus,Sigmas) = P # Unpack
        K = w.size


    (w,mus,Sigmas) = P # Unpack
    K = w.size
    dim0,dim1=dims
    if proportionInGMM is None:
        # for 95, d = 2%
        cst=2*np.sqrt(5.991)
    else:
        cst = 2*np.sqrt(chi2.isf(1-proportionInGMM, d)) # check https://www.visiondummy.com/2014/04/draw-error-ellipse-representing-covariance-matrix/
    plt.figure(figsize=(5,5))
    plt.scatter(X[:,dim0],X[:,dim1],s=1, alpha=0.15)
    ax = plt.gca()

    for k in range(K):
        mu = mus[k]
        sigma_sol = np.diag(Sigmas[k])
        plt.scatter(mu[dim0],mu[dim1],s=200*w[k],c='r')

        wEll = cst*np.sqrt(sigma_sol[dim0])
        hEll = cst*np.sqrt(sigma_sol[dim1])
        ellipse = Ellipse(xy=mu, width=wEll, height=hEll, angle = 0,
                                edgecolor='r', fc='None', lw=2)
        ax.add_patch(ellipse)


    plt.show()
    
    return


# TODO plot centroids?
