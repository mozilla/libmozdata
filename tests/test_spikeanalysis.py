# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.

import numpy as np
import unittest
from libmozdata import spikeanalysis
from libmozdata import utils
from tests.auto_mock import MockTestCase
import responses
import requests


class SpikeAnalysisTest(MockTestCase):
    mock_urls = ['https://crash-analysis.mozilla.com/rkaiser/']

    def test_get_spikes_1(self):
        x = np.zeros(1000, dtype=np.float64)
        spx = [30, 100, 250, 750]
        spy = [5678, 7123, 4123, 6183]
        x[spx] += spy

        spikes, _ = spikeanalysis.get_spikes(x, alpha=0.01, method='mean', plot=False)
        self.assertEqual(spikes, spx)

        x += 500. * np.sin(np.arange(1000, dtype=np.float64))
        spikes, _ = spikeanalysis.get_spikes(x, alpha=0.01, method='mean', plot=False)
        self.assertEqual(spikes, spx)

        spikes, _ = spikeanalysis.get_spikes(x, alpha=0.01, method='median', plot=False)
        self.assertEqual(spikes, spx)

    @responses.activate
    def test_get_spikes_2(self):
        url = 'https://crash-analysis.mozilla.com/rkaiser/Firefox-beta-crashes-categories.json'
        response = requests.get(url)
        data = response.json()

        x = {}
        max_date = utils.get_date_ymd('2016-09-09')
        for k, v in data.items():
            if 'startup' in v:
                s = v['startup']
                date = utils.get_date_ymd(k)
                if date <= max_date:
                    x[date] = s.get('browser', 0)

        up, down = spikeanalysis.get_spikes(x, alpha=0.005, win=120, method='median', plot=False)

        expected_up = [45, 46, 47, 48, 166, 169, 173, 175, 220, 221, 222, 301, 302, 346, 347, 348, 349, 355, 359, 362, 363, 366, 369, 371, 383, 384, 386, 387, 390, 391, 397, 421, 422, 423, 425, 426, 432, 434, 460, 474, 514, 533, 535, 659, 661, 690, 693, 933, 934, 935, 937, 941, 944, 945, 948]
        expected_down = [53, 332, 333, 335, 336, 337, 340, 373, 374, 375, 377, 379, 546, 547, 548, 554, 555, 560, 561, 562, 567, 568, 569, 575, 576, 726, 728]

        self.assertEqual(up, expected_up)
        self.assertEqual(down, expected_down)

    @responses.activate
    def test_is_spiking_1(self):
        url = 'https://crash-analysis.mozilla.com/rkaiser/Firefox-beta-crashes-categories.json'
        response = requests.get(url)
        data = response.json()

        x1 = {}
        x2 = {}
        max_date1 = utils.get_date_ymd('2016-09-09')
        max_date2 = utils.get_date_ymd('2016-08-05')
        for k, v in data.items():
            if 'startup' in v:
                s = v['startup']
                date = utils.get_date_ymd(k)
                if date <= max_date1:
                    x1[date] = s.get('browser', 0)
                if date <= max_date2:
                    x2[date] = s.get('browser', 0)

        isp = spikeanalysis.is_spiking(x1, alpha=0.005, win=120, method='median', plot=False)
        self.assertFalse(isp)
        isp = spikeanalysis.is_spiking(x2, alpha=0.005, win=120, method='median', plot=False)
        self.assertTrue(isp)

    @responses.activate
    def test_is_spiking_2(self):
        # values for signature nsFileStreamBase::Write from 2016-09-05 to 2016-09-13
        x = [2, 6, 6, 9, 8, 3, 2, 160, 81742]
        isp = spikeanalysis.is_spiking(x, alpha=0.01, win=-1, method='mean', plot=False)
        self.assertTrue(isp)

    @responses.activate
    def test_is_spiking_ma(self):
        url = 'https://crash-analysis.mozilla.com/rkaiser/Firefox-beta-crashes-categories.json'
        response = requests.get(url)
        data = response.json()

        x1 = {}
        x2 = {}
        max_date1 = utils.get_date_ymd('2016-09-09')
        max_date2 = utils.get_date_ymd('2016-08-05')
        for k, v in data.items():
            if 'startup' in v:
                s = v['startup']
                date = utils.get_date_ymd(k)
                if date <= max_date1:
                    x1[date] = s.get('browser', 0)
                if date <= max_date2:
                    x2[date] = s.get('browser', 0)

        y1 = [p[1] for p in sorted(x1.items(), key=lambda p: p[0])]
        y2 = [p[1] for p in sorted(x2.items(), key=lambda p: p[0])]

        isp = spikeanalysis.is_spiking_ma(y1, alpha=2.5, win=7, method='mean', plot=False)
        self.assertEqual(isp, 'none')
        isp = spikeanalysis.is_spiking_ma(y2, alpha=2.5, win=7, method='mean', plot=False)
        self.assertEqual(isp, 'up')

    @responses.activate
    def test_get_spikes_ma(self):
        # this test is quite long
        url = 'https://crash-analysis.mozilla.com/rkaiser/Firefox-beta-crashes-categories.json'
        response = requests.get(url)
        data = response.json()

        x1 = {}
        max_date1 = utils.get_date_ymd('2016-10-02')
        for k, v in data.items():
            if 'startup' in v:
                s = v['startup']
                date = utils.get_date_ymd(k)
                if date <= max_date1:
                    x1[date] = s.get('browser', 0) + s.get('content', 0) + s.get('plugin', 0)

        y1 = [p[1] for p in sorted(x1.items(), key=lambda p: p[0])]

        up, down = spikeanalysis.get_spikes_ma(y1, alpha=2.5, win=7, method='mean', plot=False)
        expected_up = [46, 47, 48, 82, 83, 84, 124, 125, 126, 127, 163, 164, 166, 169, 210, 220, 221, 222, 252, 253, 301, 302, 342, 343, 345, 346, 347, 348, 349, 383, 384, 386, 387, 422, 423, 425, 426, 460, 474, 512, 514, 533, 535, 659, 661, 689, 690, 734, 738, 757, 759, 760, 761, 852, 933, 934, 935, 944, 945]
        expected_down = [53, 60, 109, 115, 137, 144, 178, 179, 199, 200, 228, 234, 235, 308, 310, 311, 312, 332, 333, 335, 336, 337, 357, 358, 365, 373, 374, 375, 400, 401, 402, 403, 430, 431, 438, 541, 544, 545, 546, 547, 548, 667, 714, 715, 716, 726, 784, 785, 786, 916, 952, 953, 954, 960, 961]

        self.assertEqual(up, expected_up)
        self.assertEqual(down, expected_down)

    def test_generalized_esd(self):
        x = [10, 11, 9, 10, 8, 9, 12, 11, 13]
        outliers = spikeanalysis.generalized_esd(x, 5)
        self.assertEqual(outliers, [])

        x = [10, 11, 9, 10, 21, 9, 12, 11, 13]
        outliers = spikeanalysis.generalized_esd(x, 5)
        self.assertEqual(outliers, [4])

        x = [10, 11, 9, 10, 21, 9, 12, 11, 28]
        outliers = spikeanalysis.generalized_esd(x, 5)
        self.assertEqual(outliers, [8, 4])

        x = []
        outliers = spikeanalysis.generalized_esd(x, 5)
        self.assertEqual(outliers, [])


if __name__ == '__main__':
    unittest.main()
