import numpy as np
import scipy.sparse as sp
from scipy.sparse import csr_matrix

from sklearn import datasets
from sklearn.utils.testing import assert_false
from sklearn.utils.testing import assert_almost_equal
from sklearn.utils.testing import assert_array_equal
from sklearn.utils.testing import assert_equal
from sklearn.utils.testing import assert_raises_regexp
from sklearn.utils.testing import assert_raise_message
from sklearn.utils.testing import assert_greater
from sklearn.metrics.cluster import silhouette_score
from sklearn.metrics.cluster import silhouette_samples
from sklearn.metrics import pairwise_distances
from sklearn.metrics.cluster import calinski_harabaz_score


def test_silhouette():
    # Tests the Silhouette Coefficient.
    dataset = datasets.load_iris()
    X_dense = dataset.data
    X_csr = csr_matrix(X_dense)
    X_dok = sp.dok_matrix(X_dense)
    X_lil = sp.lil_matrix(X_dense)
    y = dataset.target

    for X in [X_dense, X_csr, X_dok, X_lil]:
        D = pairwise_distances(X, metric='euclidean')
        # Given that the actual labels are used, we can assume that S would be
        # positive.
        score_precomputed = silhouette_score(D, y, metric='precomputed')
        assert_greater(score_precomputed, 0)
        # Test without calculating D
        score_euclidean = silhouette_score(X, y, metric='euclidean')
        assert_almost_equal(score_precomputed, score_euclidean)

        if X is X_dense:
            score_dense_without_sampling = score_precomputed
        else:
            assert_almost_equal(score_euclidean,
                                score_dense_without_sampling)

        # Test with sampling
        score_precomputed = silhouette_score(D, y, metric='precomputed',
                                             sample_size=int(X.shape[0] / 2),
                                             random_state=0)
        score_euclidean = silhouette_score(X, y, metric='euclidean',
                                           sample_size=int(X.shape[0] / 2),
                                           random_state=0)
        assert_greater(score_precomputed, 0)
        assert_greater(score_euclidean, 0)
        assert_almost_equal(score_euclidean, score_precomputed)

        if X is X_dense:
            score_dense_with_sampling = score_precomputed
        else:
            assert_almost_equal(score_euclidean, score_dense_with_sampling)


def test_cluster_size_1():
    # Assert Silhouette Coefficient == 0 when there is 1 sample in a cluster
    # (cluster 0). We also test the case where there are identical samples
    # as the only members of a cluster (cluster 2). To our knowledge, this case
    # is not discussed in reference material, and we choose for it a sample
    # score of 1.
    X = [[0.], [1.], [1.], [2.], [3.], [3.]]
    labels = np.array([0, 1, 1, 1, 2, 2])

    # Cluster 0: 1 sample -> score of 0 by Rousseeuw's convention
    # Cluster 1: intra-cluster = [.5, .5, 1]
    #            inter-cluster = [1, 1, 1]
    #            silhouette    = [.5, .5, 0]
    # Cluster 2: intra-cluster = [0, 0]
    #            inter-cluster = [arbitrary, arbitrary]
    #            silhouette    = [1., 1.]

    silhouette = silhouette_score(X, labels)
    assert_false(np.isnan(silhouette))
    ss = silhouette_samples(X, labels)
    assert_array_equal(ss, [0, .5, .5, 0, 1, 1])


def test_silhouette_paper_example():
    # Explicitly check per-sample results against Rousseeuw (1987)
    # Data from Table 1
    lower = [5.58,
             7.00, 6.50,
             7.08, 7.00, 3.83,
             4.83, 5.08, 8.17, 5.83,
             2.17, 5.75, 6.67, 6.92, 4.92,
             6.42, 5.00, 5.58, 6.00, 4.67, 6.42,
             3.42, 5.50, 6.42, 6.42, 5.00, 3.92, 6.17,
             2.50, 4.92, 6.25, 7.33, 4.50, 2.25, 6.33, 2.75,
             6.08, 6.67, 4.25, 2.67, 6.00, 6.17, 6.17, 6.92, 6.17,
             5.25, 6.83, 4.50, 3.75, 5.75, 5.42, 6.08, 5.83, 6.67, 3.67,
             4.75, 3.00, 6.08, 6.67, 5.00, 5.58, 4.83, 6.17, 5.67, 6.50, 6.92]
    D = np.zeros((12, 12))
    D[np.tril_indices(12, -1)] = lower
    D += D.T

    names = ['BEL', 'BRA', 'CHI', 'CUB', 'EGY', 'FRA', 'IND', 'ISR', 'USA',
             'USS', 'YUG', 'ZAI']

    # Data from Figure 2
    labels1 = [1, 1, 2, 2, 1, 1, 2, 1, 1, 2, 2, 1]
    expected1 = {'USA': .43, 'BEL': .39, 'FRA': .35, 'ISR': .30, 'BRA': .22,
                 'EGY': .20, 'ZAI': .19, 'CUB': .40, 'USS': .34, 'CHI': .33,
                 'YUG': .26, 'IND': -.04}
    score1 = .28

    # Data from Figure 3
    labels2 = [1, 2, 3, 3, 1, 1, 2, 1, 1, 3, 3, 2]
    expected2 = {'USA': .47, 'FRA': .44, 'BEL': .42, 'ISR': .37, 'EGY': .02,
                 'ZAI': .28, 'BRA': .25, 'IND': .17, 'CUB': .48, 'USS': .44,
                 'YUG': .31, 'CHI': .31}
    score2 = .33

    for labels, expected, score in [(labels1, expected1, score1),
                                    (labels2, expected2, score2)]:
        expected = [expected[name] for name in names]
        # we check to 2dp because that's what's in the paper
        assert_almost_equal(expected, silhouette_samples(D, np.array(labels),
                                                         metric='precomputed'),
                            decimal=2)
        assert_almost_equal(score, silhouette_score(D, np.array(labels),
                                                    metric='precomputed'),
                            decimal=2)


def test_correct_labelsize():
    # Assert 1 < n_labels < n_samples
    dataset = datasets.load_iris()
    X = dataset.data

    # n_labels = n_samples
    y = np.arange(X.shape[0])
    assert_raises_regexp(ValueError,
                         'Number of labels is %d\. Valid values are 2 '
                         'to n_samples - 1 \(inclusive\)' % len(np.unique(y)),
                         silhouette_score, X, y)

    # n_labels = 1
    y = np.zeros(X.shape[0])
    assert_raises_regexp(ValueError,
                         'Number of labels is %d\. Valid values are 2 '
                         'to n_samples - 1 \(inclusive\)' % len(np.unique(y)),
                         silhouette_score, X, y)


def test_non_encoded_labels():
    dataset = datasets.load_iris()
    X = dataset.data
    labels = dataset.target
    assert_equal(
        silhouette_score(X, labels * 2 + 10), silhouette_score(X, labels))
    assert_array_equal(
        silhouette_samples(X, labels * 2 + 10), silhouette_samples(X, labels))


def test_non_numpy_labels():
    dataset = datasets.load_iris()
    X = dataset.data
    y = dataset.target
    assert_equal(
        silhouette_score(list(X), list(y)), silhouette_score(X, y))


def test_calinski_harabaz_score():
    rng = np.random.RandomState(seed=0)

    # Assert message when there is only one label
    assert_raise_message(ValueError, "Number of labels is",
                         calinski_harabaz_score,
                         rng.rand(10, 2), np.zeros(10))

    # Assert message when all point are in different clusters
    assert_raise_message(ValueError, "Number of labels is",
                         calinski_harabaz_score,
                         rng.rand(10, 2), np.arange(10))

    # Assert the value is 1. when all samples are equals
    assert_equal(1., calinski_harabaz_score(np.ones((10, 2)),
                                            [0] * 5 + [1] * 5))

    # Assert the value is 0. when all the mean cluster are equal
    assert_equal(0., calinski_harabaz_score([[-1, -1], [1, 1]] * 10,
                                            [0] * 10 + [1] * 10))

    # General case (with non numpy arrays)
    X = ([[0, 0], [1, 1]] * 5 + [[3, 3], [4, 4]] * 5 +
         [[0, 4], [1, 3]] * 5 + [[3, 1], [4, 0]] * 5)
    labels = [0] * 10 + [1] * 10 + [2] * 10 + [3] * 10
    assert_almost_equal(calinski_harabaz_score(X, labels),
                        45 * (40 - 4) / (5 * (4 - 1)))
