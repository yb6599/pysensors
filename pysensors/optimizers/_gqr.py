import numpy as np

from pysensors.optimizers._qr import QR

import matplotlib.pyplot as plt
from sklearn import datasets
from sklearn import metrics
from mpl_toolkits.axes_grid1 import make_axes_locatable

import pysensors as ps


class GQR(QR):
    """
    General QR optimizer for sensor selection.
    Ranks sensors in descending order of "importance" based on
    reconstruction performance. This is an extension that requires a more intrusive
    access to the QR optimizer to facilitate a more adaptive optimization. This is a generalized version of cost constraints
    in the sense that users can allow n constrained sensors in the constrained area.
    if n = 0 this converges to the CCQR results.

    See the following reference for more information
        Manohar, Krithika, et al.
        "Data-driven sparse sensor placement for reconstruction:
        Demonstrating the benefits of exploiting known patterns."
        IEEE Control Systems Magazine 38.3 (2018): 63-86.

    @ authors: Niharika Karnik (@nkarnik2999), Mohammad Abdo (@Jimmy-INL), and Krithika Manohar (@kmanohar)
    """
    def __init__(self,idx_constrained,n_sensors,const_sensors):
        """
        Attributes
        ----------
        pivots_ : np.ndarray, shape [n_features]
            Ranked list of sensor locations.
        idx_constrained : np.ndarray, shape [No. of constrained locations]
            Column Indices of the sensors in the constrained locations.
        n_sensors : integer, 
            Total number of sensors
        const_sensors : integer,
            Total number of sensors required by the user in the constrained region.
        """
        self.pivots_ = None
        self.constrainedIndices = idx_constrained
        self.nSensors = n_sensors
        self.nConstrainedSensors = const_sensors

    def fit(
        self,
        basis_matrix
    ):
        """
        Parameters
        ----------
        basis_matrix: np.ndarray, shape [n_features, n_samples]
            Matrix whose columns are the basis vectors in which to
            represent the measurement data.
        optimizer_kws: dictionary, optional
            Keyword arguments to be passed to the qr method.

        Returns
        -------
        self: a fitted :class:`pysensors.optimizers.QR` instance
        """

        n_features, n_samples = basis_matrix.shape  # We transpose basis_matrix below
        max_const_sensors = len(self.constrainedIndices) #Maximum number of sensors allowed in the constrained region

        ## Assertions and checks:
        if self.nSensors > n_features - max_const_sensors + self.nConstrainedSensors:
            raise IOError ("n_sensors cannot be larger than n_features - all possible locations in the constrained area + allowed constrained sensors")
        if self.nSensors > n_samples + self.nConstrainedSensors: ## Handling zero constraint?
            raise IOError ("Currently n_sensors should be less than number of samples + number of constrained sensors,\
                           got: n_sensors = {}, n_samples + const_sensors = {} + {} = {}".format(n_sensors,n_samples,self.nConstrainedSensors,n_samples+self.nConstrainedSensors))

        # Initialize helper variables
        R = basis_matrix.conj().T.copy()
        p = np.arange(n_features)
        k = min(n_samples, n_features)


        for j in range(k):
            r = R[j:, j:]
            # Norm of each column
            dlens = np.sqrt(np.sum(np.abs(r) ** 2, axis=0))
            dlens_updated = f_region(self.constrainedIndices,dlens,p,j, self.nConstrainedSensors) #Handling constrained region sensor placement problem
            
            # Choose pivot
            i_piv = np.argmax(dlens_updated)
          
            dlen = dlens_updated[i_piv]

            if dlen > 0:
                u = r[:, i_piv] / dlen
                u[0] += np.sign(u[0]) + (u[0] == 0)
                u /= np.sqrt(abs(u[0]))
            else:
                u = r[:, i_piv]
                u[0] = np.sqrt(2)

            # Track column pivots
            i_piv += j # true permutation index is i_piv shifted by the iteration counter j
            p[[j, i_piv]] = p[[i_piv, j]]

            # Switch columns
            R[:, [j, i_piv]] = R[:, [i_piv, j]]

            # Apply reflector
            R[j:, j:] -= np.outer(u, np.dot(u, R[j:, j:]))
            R[j + 1 :, j] = 0

        self.pivots_ = p


        return self

## TODO: why not a part of the class?

#function for mapping sensor locations with constraints
def f_region(lin_idx, dlens, piv, j, const_sensors):
    #num_sensors should be fixed for each custom constraint (for now)
    #num_sensors must be <= size of constraint region
    """
    Function for mapping constrained sensor locations with the QR procedure.

    Parameters
        ----------
        lin_idx: np.ndarray, shape [No. of constrained locations]
            Array which contains the constrained locationsof the grid in terms of column indices of basis_matrix.
        dlens: np.ndarray, shape [Variable based on j]
            Array which contains the norm of columns of basis matrix.
        piv: np.ndarray, shape [n_features]
            Ranked list of sensor locations.
        const_sensors: int,
            Number of sensors to be placed in the constrained area.
        j: int,
            Iterative variable in the QR algorithm.

        Returns
        -------
        dlens : np.darray, shape [Variable based on j] with constraints mapped into it.
    """
    if j < const_sensors: # force sensors into constraint region
        #idx = np.arange(dlens.shape[0])
        #dlens[np.delete(idx, lin_idx)] = 0

        didx = np.isin(piv[j:],lin_idx,invert=True)
        dlens[didx] = 0
    else:
        didx = np.isin(piv[j:],lin_idx,invert=False)
        dlens[didx] = 0
    return dlens

def getConstraindSensorsIndices(xmin, xmax, ymin, ymax, all_sensors):
    """
    Function for mapping constrained sensor locations on the grid with the column indices of the basis_matrix.

    Parameters
        ----------
        xmin: int, 
            "Fill"
        xmax : int,
            "Fill"
        ymin : int,
            "Fill"
        ymax : int
            "Fill"
        all_sensors : np.ndarray, shape [n_features]
            Ranked list of sensor locations.

        Returns
        -------
        idx_constrained : np.darray, shape [No. of constrained locations] 
            Array which contains the constrained locationsof the grid in terms of column indices of basis_matrix.
    """
    n_features = len(all_sensors)
    imageSize = int(np.sqrt(n_features))
    a = np.unravel_index(all_sensors, (imageSize,imageSize))
    constrained_sensorsx = []
    constrained_sensorsy = []
    for i in range(n_features):
        if (a[0][i] >= xmin and a[0][i] <= xmax) and (a[1][i] >= ymin and a[1][i] <= ymax):  # x<10 and y>40
            constrained_sensorsx.append(a[0][i])
            constrained_sensorsy.append(a[1][i])

    constrained_sensorsx = np.array(constrained_sensorsx)
    constrained_sensorsy = np.array(constrained_sensorsy)
    constrained_sensors_array = np.stack((constrained_sensorsy, constrained_sensorsx), axis=1)
    constrained_sensors_tuple = np.transpose(constrained_sensors_array)
    if len(constrained_sensorsx) == 0: ##Check to handle condition when number of sensors in the constrained region = 0
        idx_constrained = []
    else:
        idx_constrained = np.ravel_multi_index(constrained_sensors_tuple, (imageSize,imageSize))
    return idx_constrained

def boxConstraints(position,lowerBound,upperBound,):
    for i,xi in enumerate(position):
        f1 = position[i] - lowerBound[i]
        f2 = upperBound[i] - position [i]
    return +1 if (f1 and f2 > 0) else -1

def functionalConstraint(position, func_response,func_input, freeTerm):
    g = func_response + func_input + freeTerm
    return g


if __name__ == '__main__':
    pass
    faces = datasets.fetch_olivetti_faces(shuffle=True)
    X = faces.data

    n_samples, n_features = X.shape
    print('Number of samples:', n_samples)
    print('Number of features (sensors):', n_features)

    # Global centering
    X = X - X.mean(axis=0)

    # Local centering
    X -= X.mean(axis=1).reshape(n_samples, -1)

    n_row, n_col = 2, 3
    n_components = n_row * n_col
    image_shape = (64, 64)

    def plot_gallery(title, images, n_col=n_col, n_row=n_row, cmap=plt.cm.gray):
        '''Function for plotting faces'''
        plt.figure(figsize=(2. * n_col, 2.26 * n_row))
        plt.suptitle(title, size=16)
        for i, comp in enumerate(images):
            plt.subplot(n_row, n_col, i + 1)
            vmax = max(comp.max(), -comp.min())
            plt.imshow(comp.reshape(image_shape), cmap=cmap,
                    interpolation='nearest',
                    vmin=-vmax, vmax=vmax)
            plt.xticks(())
            plt.yticks(())
        plt.subplots_adjust(0.01, 0.05, 0.99, 0.93, 0.04, 0.)

   # plot_gallery("First few centered faces", X[:n_components])

    #Find all sensor locations using built in QR optimizer
    max_const_sensors = 230
    n_const_sensors = 7
    n_sensors = 50
    optimizer  = ps.optimizers.QR()
    model = ps.SSPOR(optimizer=optimizer, n_sensors=n_sensors)
    model.fit(X)

    all_sensors = model.get_all_sensors()

    ##Constrained sensor location on the grid: 
    xmin = 20
    xmax = 40
    ymin = 25
    ymax = 45
    sensors_constrained = getConstraindSensorsIndices(xmin,xmax,ymin,ymax,all_sensors) #Constrained column indices 

    ##Plotting the constrained region
    # ax = plt.subplot()
    # #Plot constrained space
    # img = np.zeros(n_features)
    # img[sensors_constrained] = 1
    # im = plt.imshow(img.reshape(image_shape),cmap=plt.cm.binary)
    # # create an axes on the right side of ax. The width of cax will be 5%
    # # of ax and the padding between cax and ax will be fixed at 0.05 inch.
    # divider = make_axes_locatable(ax)
    # cax = divider.append_axes("right", size="5%", pad=0.05)
    # plt.colorbar(im, cax=cax)
    # plt.title('Constrained region');

    ## Fit the dataset with the optimizer GQR
    optimizer1 = GQR(sensors_constrained,n_sensors,n_const_sensors)
    model1 = ps.SSPOR(optimizer = optimizer1, n_sensors = n_sensors)
    model1.fit(X)
    all_sensors1 = model1.get_all_sensors()

    top_sensors = model1.get_selected_sensors()
    print(top_sensors)
    ## TODO: this can be done using ravel and unravel more elegantly
    yConstrained = np.floor(top_sensors[:n_const_sensors]/np.sqrt(n_features))
    xConstrained = np.mod(top_sensors[:n_const_sensors],np.sqrt(n_features))

    img = np.zeros(n_features)
    img[top_sensors[n_const_sensors:]] = 16
    plt.plot(xConstrained,yConstrained,'*r')
    plt.plot([xmin,xmin],[ymin,ymax],'r')
    plt.plot([xmin,xmax],[ymax,ymax],'r')
    plt.plot([xmax,xmax],[ymin,ymax],'r')
    plt.plot([xmin,xmax],[ymin,ymin],'r')
    plt.imshow(img.reshape(image_shape),cmap=plt.cm.binary)
    plt.title('n_sensors = {}, n_constr_sensors = {}'.format(n_sensors,n_const_sensors))
    plt.show()
