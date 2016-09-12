# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import scipy.stats as stats
import numpy as np
import matplotlib.pyplot as plt


def __get_grubb_lambda(n, alpha):
    """Get the value to use for the Grubb's test
       http://www.itl.nist.gov/div898/handbook/eda/section3/eda35h1.htm

    Args:
        n (int): the number of elements in the sample
        alpha (float): the signifiance level

    Returns:
        float: the critical value to use
    """
    n = float(n)
    p = alpha / (2. * n)
    t = np.abs(stats.t.ppf(p, n - 2.))
    l = (n - 1.) * t / np.sqrt((n - 2. + t ** 2) * n)

    return l


def __get_pd_median(data):
    """Get the median and the mad of data

    Args:
        data (numpy.ndarray): the data

    Returns:
        float, float: the median and the mad
    """
    p = np.nanmedian(data)
    d = np.nanmedian(np.abs(data - p))  # d is the MAD

    return p, d


def __get_pd_mean(data):
    """Get the mean and the standard deviation of data

    Args:
        data (numpy.ndarray): the data

    Returns:
        float, float: the mean and the standard deviation
    """
    p = np.nanmean(data)
    d = np.nanstd(data)

    return p, d


def get_spikes(data, alpha=0.05, win=-1, threshold_up=-float('Inf'), threshold_down=+float('Inf'), method='median', plot=False):
    """Get the spikes in data.
       The Grubb's test is applyed to determinate if a value is an outlier or not (http://www.itl.nist.gov/div898/handbook/eda/section3/eda35h1.htm)

    Args:
        data (numpy.ndarray): the data
        alpha (float): the signifiance level
        win (int): the size of the window to use to compute the parameters
        threshold_up (float): the min value to say that a spike is a spike
        threshold_down (float): the min value to say that a spike is a spike
        method (str): 'median' or 'mean'
        plot (Bool): True if a plot is wanted

    Returns:
        list[int], list[int]: the index of the spikes (up and down)
    """

    # TODO:
    # It could be interesting to remove the noise in using wavelets.
    # And maybe we could use them to detect the outliers too.

    if isinstance(data, dict):
        data = [i[1] for i in sorted(data.items(), key=lambda p: p[0])]
    if isinstance(data, list):
        data = np.asarray(data, dtype=np.float64)

    fn = __get_pd_median if method == 'median' else __get_pd_mean
    _data = np.copy(data)
    NaN = float('nan')
    spikes_up = []
    spikes_down = []

    for i in range(3, len(data) + 1):
        start = max(0, i - win) if win > 0 else 0
        d = _data[start:i]
        x = d[-1]
        N = d.size - np.isnan(d).sum()  # number of non NaN values
        m, e = fn(d)
        l = __get_grubb_lambda(N, alpha)
        th = l * e
        if abs(x - m) > th:  # Grubb's test
            _data[i - 1] = NaN  # to ignore this outlier in the future
            if x > m + th and x >= threshold_up and x > data[i - 2]:
                spikes_up.append(i - 1)
            elif x < m - th and x <= threshold_down and x < data[i - 2]:
                spikes_down.append(i - 1)

    if plot:
        fig = plt.figure()
        ax = fig.add_subplot(111)
        X = np.arange(len(data))
        Y = data
        ax.plot(X, Y, color='blue')
        if spikes_up:
            ax.plot(X[spikes_up], Y[spikes_up], 'ro', color='red')
        if spikes_down:
            ax.plot(X[spikes_down], Y[spikes_down], 'ro', color='green')
        plt.show()

    return spikes_up, spikes_down


def is_spiking(data, alpha=0.05, win=-1, threshold_up=-float('Inf'), threshold_down=+float('Inf'), method='median', plot=False):
    """Check if the last value is a spike (up).

    Args:
        data (numpy.ndarray): the data
        alpha (float): the signifiance level
        win (int): the size of the window to use to compute the parameters
        threshold_up (float): the min value to say that a spike is a spike
        threshold_down (float): the min value to say that a spike is a spike
        method (str): 'median' or 'mean'
        plot (Bool): True if a plot is wanted

    Returns:
        Bool: True if the last value is a spike (up).
    """
    up, _ = get_spikes(data, alpha=alpha, win=win, threshold_up=threshold_up, threshold_down=threshold_down, method=method, plot=plot)
    return up and up[-1] == len(data) - 1
