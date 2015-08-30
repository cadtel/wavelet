import pdb
import numpy as np
import matplotlib.pyplot as plt


# --- wavelet transforms ---
def db2(S, MAX_LAYER = -1):
    #forward discrete wavelet transform db2 (1 vanishing moment)
    #S: array full of data
    #T: number of elements evaluated

    N = len(S)
    T = N
    
    #if N is not a power of 2
    if N & (N-1) != 0 and N > 0:
        #find lowest power of 2 greater than N
        p2 = 1 << (N).bit_length()
        #pad with zeros up to N
        #make sure that array can be resized
        S.resize(p2, refcheck=False)
        print S
        T = p2
    
    layers = 0
    step = 2
    
    while step < 2*T:
        if (MAX_LAYER >= 0) and (layers >= MAX_LAYER): break

        start = step/2
        
        #predict 1
        S[start::step] -= S[::step]

        #update 1
        S[::step] += S[start::step]/2
         
        step <<= 1
        layers += 1
    
    return S

def idb2(W, MAX_LAYER = -1):
    N = len(W)

    layers = 0
    step = N

    #magic
    #if a max number of layers is specified, lower step so the high freq are processed
    if (((N).bit_length() - 1) >=MAX_LAYER >= 0): step = 1 << MAX_LAYER
    
    while step > 1:
        start = step/2
        
        #update' 1
        W[::step] -= W[start::step]/2
        
        #predict' 1
        W[start::step] += W[::step]

        step >>= 1
        layers += 1

    return W


def db4(S, MAX_LAYER = -1):
    #forward discrete wavelet transform    
    #S: array full of data
    #T: number of elements evaluated

    #split array, first half are even elements and second half are odd element
    N = len(S)
    T = N
    
    #if N is not a power of 2
    if N & (N-1) != 0 and N > 0:
        #find lowest power of 2 greater than N
        p2 = 1 << (N).bit_length()
        #pad with zeros up to N        S.resize(p2, refcheck=False)
        print S
        T = p2
    

    s3 = np.sqrt(3)
    s2 = np.sqrt(2)
    
    layers = 0
    step = 2
    
    while step < 2*T:
        if (MAX_LAYER >= 0) and (layers >= MAX_LAYER): break

        start = step/2
        
        #update
        S[::step]  += s3 * S[start::step]
        
        #predict
        S[(start+step) :: step] += - s3/4*S[step::step] - (s3-2)/4*S[:-step:step] 
        S[start] += - s3/4*S[0] - (s3-2)/4*S[-step]
        
        #update 2
        S[:-step:step]  = S[:-step:step]  - S[(start+step) :: step]
        S[-step] = S[-step] - S[start]
        
        #normalize
        S[::step]  = (s3-1)/s2 * S[::step]  
        S[start::step] = (s3+1)/s2*S[start::step]
        
        step <<= 1
        layers += 1
        
    return S
    
def idb4(W, MAX_LAYER = -1):
    #inverse discrete wavelet transform    
    #same as forward, except all additions and subtractions are flipped
    #W: array full of wavelet coefficients
    #MAX_LAYER: total level of coefficients in transform
    #  It is possible for a transform to be partial, such as data with size 2^16 to go 8 levels deep instead of 16
 
    N = len(W)
    s3 = np.sqrt(3)
    s2 = np.sqrt(2)

    layers = 0
    step = N
    
    #if a max number of layers is specified, lower step so the high freq are processed
    if (((N).bit_length() - 1) >= MAX_LAYER >= 0): step = 1 << MAX_LAYER
    
    while step > 1:
        start = step/2

        #normalize'
        W[::step] = (s3+1)/s2 * W[::step]
        W[start::step] = (s3-1)/s2 * W[start::step]

        #update 2'
        W[:-step:step] = W[:-step:step] + W[(start+step) :: step]
        W[-step] = W[-step] + W[start]
        
        #predict'        
        W[(start+step) :: step] += + s3/4*W[step::step]  + (s3-2)/4*W[:-step:step]
        W[start] += + s3/4*W[0] + (s3-2)/4*W[-step]
        
        #update 1'
        W[::step] += -s3 * W[start::step]
        
        step >>= 1
            
    return W

def dwt(S, MAX_LAYER = -1, wavelet = "db4"):
    if wavelet == "db2" or wavelet == "haar":
        return db2(S,  MAX_LAYER = MAX_LAYER)
    elif wavelet == "db4":
        return db4(S, MAX_LAYER = MAX_LAYER)
    #elif wavelet == "db6":
    #    return db6(S, MAX_LAYER = MAX_LAYER)
    else:
        return db4(S, MAX_LAYER = MAX_LAYER)
    
def idwt(W, MAX_LAYER = -1, wavelet = "db4"):
    if wavelet == "db2" or wavelet == "haar":
        return idb2(W,  MAX_LAYER = MAX_LAYER)
    elif wavelet == "db4":
        return idb4(W, MAX_LAYER = MAX_LAYER)
    #elif wavelet == "db6":
    #    return idb6(W, MAX_LAYER = MAX_LAYER)
    else:
        return idb4(W, MAX_LAYER = MAX_LAYER)   

# --- coefficient ordering ---
def layer_to_interlace(old):
    T = len(old)
    new = np.zeros(T)
    step = 2
    while T > 1:
        half = T/2
        start = step/2
        new[start::step] = old[half:T]

        start <<= 1
        T >>= 1
    new[0] = old[0]
    return new

def interlace_to_layer(old):
    T = len(old)
    new = np.zeros(T)
    step = 2
    while T > 1:
        half = T/2
        start = step/2
        new[half:T] = old[start::step]

        step <<= 1
        T >>= 1
    new[0] = old[0]
    return new

# --- thresholding and denoising ---
def threshold(W, LAM = -1,  MAX_LAYER = -1, N_ELEMENTS = 0, shrink = "hard", policy = "none"):
    #W: array full of wavelet coefficients
    #Possible flags, choice between:
    #   LAM: set threshold value
    #   MAX_LAYER: how many layers in transform
    #   N_ELEMENTS: preserve number of wavelet coefficients
    #   SHRINK: "hard", "soft", "semisoft"
    #   POLICY: none, universal, SURE
    
    #if THRESHOLD is an integer, THRESHOLD is applied on every level
    #if it is an array, then THRESHOLD is level dependent
    
    #Warning: Horrible code. Need to completely rehaul.
    
    shrink = shrink.lower()
    policy = policy.lower()
    N = len(W)
    logN = (N).bit_length() - 1
    
    shrinkage = False
    
    if LAM > 0:
        THRESHOLD = LAM
    
    elif policy != "none":
        
        start = 1
        step = 2
        
        if policy == "universal":
            #universal thresholding is the upper bound
            #doesnt matter whether hard, soft, or semisoft are used
            median = np.median(abs(W[start:step]))
            THRESHOLD = median/0.6745*np.sqrt(2.0*(logN-1))

        """
        elif policy == "universal_level" and MAX_LAYER > 0:
            layer = 0
            THRESHOLD = []
            while layer < MAX_LAYER-1 and i > 0:
                lni = (i).bit_length() - 1
                median = np.median(abs(W[i:j]))
                THRESHOLD.append(median/0.6745*np.sqrt(2.0*lni))
                i >>= 1
                j >>= 1
        """

        """        
        elif policy == "sure" and MAX_LAYER > 0:
            #sure stuff goes here
            #requires soft thresholding
            THRESHOLD = []
            shrink = "soft"
            layer = 0
            while layer < MAX_LAYER-1 and i > 0:
                #pdb.set_trace()
                w_target = W[i:j]
                sigma = np.median(np.abs(w_target))/0.6745
                s = lambda t: sure(w_target, t, sigma)
                lni = np.log(i)
                t0 = sigma*np.sqrt(2.0*lni)
                #threshold minimizes SURE
                #start with universal/2
                t = opt.minimize(fun = s, x0 = t0/2, bounds = [[0, t0]])
                nu = sure_sparsity(w_target)
                if nu <= 1: t = t0
                THRESHOLD.append(t)
                i >>= 1
                j >>= 1
        """
                        
        #elif policy == "neighcoeff" and MAX_LAYER > 0:
        #    while layer < MAX_LAYER - 1 and i > 0:
        #        pass
                                
        
    elif N_ELEMENTS > 0:
        #THRESHOLD = sorted([abs(i) for i in W], reverse=True)[N_ELEMENTS]
        THRESHOLD = np.abs(W[np.argpartition(-np.abs(W), N_ELEMENTS)[N_ELEMENTS]])
        
        shrink = "hard"
        
        
    else:
        return W
    
    
    if type(THRESHOLD) != list and type(THRESHOLD) != np.ndarray:
       # print "Constant Threshold:", THRESHOLD
        W[np.abs(W) < THRESHOLD] = 0.0
        if shrink == "soft":
            W[np.abs(W) >= THRESHOLD] -= THRESHOLD * np.sign(W[np.abs(W) >= THRESHOLD])
           # print "soft threshold"
        
        elif shrink == "semisoft":
            W[np.abs(W) >= THRESHOLD] = np.sqrt(W[np.abs(W) >= THRESHOLD]**2 - THRESHOLD**2) * np.sign(W[np.abs(W) >= THRESHOLD])

    """    
    elif type(THRESHOLD) == list:
        #TODO
        i = N/2
        j = N
        c = 0
        if MAX_LAYER < 0: MAX_LAYER = logN
        while c < MAX_LAYER and c < len(THRESHOLD) and i > 0:
            #repeated indexing is compiler optimized away
            t = THRESHOLD[c]
            #print t
            W[i:j][np.abs(W[i:j]) < t] = 0.0
            if shrink == "soft":
                W[i:j][abs(W[i:j]) >= t] -= t * np.sign(W[i:j][abs(W[i:j]) >= t])
                #print "soft threshold"
        
            elif shrink == "semisoft":
                W[i:j][abs(W[i:j]) >= t] = np.sqrt(W[i:j][abs(W[i:j]) >= t]**2 - t**2) * np.sign(W[i:j][abs(W[i:j]) >= t])

            i >>= 1
            j >>= 1
            
            c += 1
    """
    return W
    
# --- printing and plotting ---
def waveletprint(W, MAX_LAYER = -1):
    N = len(W)
    logn = (N).bit_length() - 1
    
    initstep = N
    if logn > MAX_LAYER >= 0:
        initstep  >>= (logn - MAX_LAYER)
        
    step = initstep
    scale = 0
    print initstep

    lowdone = False
    if step == 1:
        print "\nScale 2^0:", W
        
    while step > 1:
        #stuff
        if step==initstep and not lowdone:
            start = 0
            lowdone = True
            sl = W[::step]
        else:
            start = step >> 1
            sl = W[start::step]
            step >>= 1

        st = "\nScale 2^-" + str(scale) + ":"
        print st, sl
        scale += 1


# --- test functions ---
def doppler(t):
    return np.sqrt(t*(t+1)) * np.sin(2*np.pi*1.05/(t+0.05))

def sinusoid(t):
    return np.sin(2 * np.pi * 4 * t)

def blocks(t):
    K = lambda c: (1 + np.sign(c))/2.0
    x = np.array([[.1, .13, .15, .23, .25, .4, .44, .65, .76, .78, .81]]).T
    h = np.array([[4, -5, 3, -4, 5, -4.2, 2.1, 4.3, -3.1, 2.1, -4.2]]).T
    return np.sum(h*K(t/2 - x), axis=0)
    
def bumps(t):
    K = lambda c : (1. + np.abs(c)) ** -4.
    x = np.array([[.1, .13, .15, .23, .25, .4, .44, .65, .76, .78, .81]]).T
    h = np.array([[4, 5, 3, 4, 5, 4.2, 2.1, 4.3, 3.1, 2.1, 4.2]]).T
    w = np.array([[.005, .005, .006, .01, .01, .03, .01, .01, .005, .008, .005]]).T
    return np.sum(h*K((x-t/2)/w), axis=0)    
    
def heavisine(t):
    return 4 * np.sin(2*np.pi*t) - np.sign(t/2 - 0.3) - np.sign(0.72 - t/2)


# --- plots and accuracy ---
def psnr(truth, estimate):
    #returns Peak Signal to Noise Ratio in decibels
    N = len(truth)
    mean = np.mean(truth)
    #num = sum([abs(truth[i] - mean)**2 for i in range(N)])
    num = np.sum(truth ** 2)
    denom = np.sum((truth-estimate)**2)
    snr = 10 * np.log10(num/denom)
    
    return snr

def approx_plot(t, W, MAX_LAYER = -1, wavelet = "db4"):
    #sequence of approximations plotted, each with 1/2 as much data as the previous
    N = len(W)
    logN = (N).bit_length() - 1
    
    #if a max number of layers is specified, lower step so the high freq are processed
    if (logN >= MAX_LAYER >= 0):
        step = 1 << MAX_LAYER
    else:
        step = N
        MAX_LAYER = logN


    if wavelet == "db2" or wavelet == "haar":
        factor = 1
    elif wavelet == "db4":
        factor = 1/np.sqrt(2)
        
    curr_factor = 1.0
    step = 1
    fig = plt.figure()
    ax = fig.add_subplot(111)
    
    for level in range(MAX_LAYER, 0, -1):
        #use approximation
        ids = idwt(np.copy(W[::step]), level, wavelet)
        ids *= curr_factor
        ts = t[step/2::step]
        name = "truth" if level == MAX_LAYER else "level" + str(level)
        ax.plot(ts, ids, label = name)
        
        curr_factor *= factor
        step <<= 1
 
    ax.legend(loc = "lower right")
    return fig


def coeff_pyramid(t, W, MAX_LAYER = -1, wavelet = "db4"):
    #2 plots, a coefficient stem plot, and a plot showing the bases (inverse of each layer of coefficients)
    N = len(W)
    logN = (N).bit_length() - 1
    
    #if a max number of layers is specified, lower step so the high freq are processed
    if (logN >= MAX_LAYER >= 0):
        step = 1 << MAX_LAYER
    else:
        step = N
        MAX_LAYER = logN
    
    fig, axs = plt.subplots(MAX_LAYER+1, 1, sharex = True)
    fig2, axs2 = plt.subplots(MAX_LAYER+1, 1, sharex = True, sharey = True)
    i = 0
    
    T = N >> (MAX_LAYER)
    Fs = 1 / (t[1]-t[0])
    
    currplot = 0
    max_freq = Fs / (1 << (MAX_LAYER - 1))
    
    while step > 1:
        start = step >> 1
        layer_t = t[start::step]
        
        w_empty = np.zeros(N)
        
        if i == 0:
            title_str = "Scaling Coeff (0 - {:.2f} Hz)".format(Fs /(1 << (MAX_LAYER - 1)))
            layer_w = W[::step]
            axs[i].set_title(title_str)
            axs2[i].set_title(title_str)
            w_empty[::step] = W[::step]
        
        else:
            title_str = "Wavelet Coeff level {:x} ({:.2f} - {:.2f} Hz)".format(i-1, max_freq, max_freq*2)
            axs[i].set_title(title_str)
            axs2[i].set_title(title_str)
            
            max_freq *= 2
            layer_w = W[start::step]
            w_empty[start::step] = W[start::step]
            
            step >>= 1
            
        #pdb.set_trace()
        
        axs[i].stem(layer_t, layer_w, basefmt = "black", markerfmt = " ")
        idw = idwt(np.copy(w_empty), MAX_LAYER, wavelet)
        axs2[i].plot(t, idw)

        i += 1
        
    return fig 

if __name__ == "__main__":
    #s = np.array([32.0, 10.0, 20.0, 38.0, 37.0, 28.0, 38.0, 34.0, 18.0, 24.0, 18.0, 9.0, 23.0, 24.0, 28.0, 34.0])
    #s = np.arange(8, dtype = np.float64)
    #s = np.array([9.0, 7.0, 3.0, 5.0])
    #s = np.array([1.0, -1.0, 1.0, -1.0, 1.0, -1.0, 1.0, -1.0])
    #s = np.array([1.0, 3.0, -2.0, 1.5, -0.5, 2.0, 0.0, 1.0])
    N = 1024
    x = np.linspace(0, 2, N)
    sigma = 0.35
    noise = np.random.normal(loc = 0.0, scale = sigma, size = N)
    s = heavisine(x)
    rs = s + noise
    ml = 7
    wavelet_type = "db4"
    #print s
    ds = dwt(np.copy(s), MAX_LAYER = ml, wavelet = wavelet_type)
    drs = dwt(np.copy(rs), MAX_LAYER = ml, wavelet = wavelet_type)
    #print ds
    #print interlace_to_layer(ds)
    ids = idwt(np.copy(ds), MAX_LAYER = ml, wavelet = wavelet_type)
    #print ids

    #waveletprint(ds, MAX_LAYER = ml)
    #coeff_pyramid(x, ds, MAX_LAYER = ml, wavelet = wavelet_type)
    #approx_plot(x, ds, MAX_LAYER = ml, wavelet = wavelet_type)


    drst = threshold(drs, policy = "universal")
    
    #coeff_pyramid(x, ds2, MAX_LAYER = ml, wavelet = wavelet_type)
    #approx_plot(x, ds2, MAX_LAYER = ml, wavelet = wavelet_type)

    idrst = idwt(np.copy(drst), MAX_LAYER = ml, wavelet = wavelet_type)
    psnrt = psnr(s, ids)
    psnr1 = psnr(s, rs)
    psnr2 = psnr(s, idrst)

    fig = plt.figure()
    ax = fig.add_subplot(111)
    ax.plot(x, s, label = "Ground Truth ({:.2f} dB)".format(psnrt))
    ax.plot(x, rs, label = "Noisy Data ({:.2f} dB)".format(psnr1))
    ax.plot(x, idrst, label = "Univ Threshold ({:.2f} dB)".format(psnr2))
    ax.legend(loc = "lower right")

    plt.show()
    
