from Packages import *
from Initialisations import *

class WakeNet(nn.Module):

    def __init__(self, inputs = 3, hiddenSize = 100, hiddenSize2 = 100):
        """
        WakeNet initializations

        Args:
            u_stream (torch float array) Inputs of training step.
            points (int): Number of individual sub-network to be trained.
            ws (float) Wind speed.
            ti (float) Turbulence intensity.
            yw (float) Yaw angle.
            hb (float) Hub height.
            model (torch model) Passes the neural model to be used.
            timings (boolean, optional) Prints and output timings of both Neural
                and Analytical calculations.

        Returns:
            gauss_time, neural_time, error (floats) Analytical, Neural timings and 
                absolute mean error between the Analytical and Neural wake deficits.

            or
            
            final (2D numpy float array) Wake profile with u_stream background velocity.
        """

        super(WakeNet, self).__init__()

        # Parameters
        inputSize = inputs
        outputSize = out_piece
        points = rows

        # Initialisation of linear layers
        self.fc1 = []
        self.fc2 = []
        self.fc3 = []

        # Append independent sub-networks in parallel
        for _ in range(points):
            self.fc1.append(nn.Linear(inputSize, hiddenSize, bias = True).to(device))

            self.fc2.append(nn.Linear(hiddenSize, hiddenSize2, bias = True).to(device))

            self.fc3.append(nn.Linear(hiddenSize2, outputSize, bias = True).to(device))

        # Batch normalisation layers
        self.fc15 = nn.BatchNorm1d(hiddenSize)
        self.fc25 = nn.BatchNorm1d(hiddenSize2)

        # Dropout
        self.drop = nn.Dropout(0.5) # 50% probability

        # Activation functions
        self.act = nn.Tanh()
        # self.act = nn.Sigmoid()
        # self.act = self.tansig
        # self.act2 = nn.Sigmoid()
        self.act2 = self.purelin


    def tansig(self, s):
        return 2 / (1 + torch.exp(-2*s)) - 1


    def purelin(self, s):
        return s


    def forward(self, X, point):
        """
        Performs a forward step during training.

        Args:
            X (torch float array) Inputs of training step.
            point (int): Number of individual sub-network to be trained.

        Returns:
            out (torch float array) Turbine wake output.
        """

        X = X.to(device)
        if synth == 0:
            X = X.view(1, -1)
        X = self.fc15(self.act(self.fc1[point](X)))
        # X = self.drop(X)  # dropout (unused)

        if synth == 0:
            X = X.view(1, -1)
        X = self.fc25(self.act(self.fc2[point](X)))
        # X = self.drop(X)  # dropout (unused)

        out = self.act2(self.fc3[point](X))

        return out


    def saveWeights(self, model):
        torch.save(model, "NN")


    def CompareContour(self, 
                       u_stream,
                       points, 
                       ws, 
                       ti, 
                       yw, 
                       hb, 
                       model, 
                       result_plots=result_plots, 
                       timings=False):
        """
        Performs a forward step during training.

        Args:
            u_stream (torch float array) Inputs of training step.
            points (int): Number of individual sub-network to be trained.
            ws (float) Wind speed.
            ti (float) Turbulence intensity.
            yw (float) Yaw angle.
            hb (float) Hub height.
            model (torch model) Passes the neural model to be used.
            timings (boolean, optional) Prints and output timings of both Neural
                and Analytical calculations.

        Returns:
            gauss_time, neural_time, error (floats) Analytical, Neural timings and 
                absolute mean error between the Analytical and Neural wake deficits.

            or
            
            final (2D numpy float array) Wake profile with u_stream background velocity.
        """

        # Random Dataset
        np.random.seed(89)
        speeds = np.random.rand(data_size)*(ws_range[1] - ws_range[0]) + ws_range[0]   # hub inlet speeds
        np.random.seed(42)
        tis = np.random.rand(data_size)*(ti_range[1] - ti_range[0]) + ti_range[0]      # turbulence intensities
        np.random.seed(51)
        yws = (np.random.rand(data_size) - 0.5)*(yw_range[1] - yw_range[0])            # hub yaw angles
        np.random.seed(256)
        hbs = np.random.rand(data_size)*(hb_range[1] - hb_range[0]) + hb_range[0]      # height slice


        # Keep mean and std of data to normalise later
        smean, tmean, ymean, hmean = np.mean(speeds), np.mean(tis), np.mean(yws), np.mean(hbs)
        sstd, tstd, ystd, hstd = np.std(speeds), np.std(tis), np.std(yws), np.std(hbs)
        
        if timings == True or result_plots == True:

            t0 = time.time()
            
            # Set Floris parameters

            # fi.floris.farm.set_wake_model('curl')  # curl model

            if inputs == 1:
                fi.reinitialize_flow_field(wind_speed = ws)
                fi.calculate_wake()
            if inputs == 2:
                fi.reinitialize_flow_field(wind_speed = ws)
                fi.reinitialize_flow_field(turbulence_intensity = ti)
                fi.calculate_wake()
            if inputs == 3:
                fi.reinitialize_flow_field(wind_speed = ws)
                fi.reinitialize_flow_field(turbulence_intensity = ti)
                # fi.change_turbine([0],{'yaw_angle':yw})
                fi.calculate_wake(yaw_angles=yw)

            # fi.calculate_wake()

            if inputs == 4:
                fi.reinitialize_flow_field(wind_speed = ws)
                fi.reinitialize_flow_field(turbulence_intensity = ti)
                fi.change_turbine([0],{'yaw_angle':yw})
                cut_plane = fi.get_hor_plane(height=hb,
                                             x_resolution=dimx,
                                             y_resolution=dimy,
                                             x_bounds=x_bounds,
                                             y_bounds=y_bounds)
            else:
                cut_plane = fi.get_hor_plane(height=hh,
                                             x_resolution=dimx,
                                             y_resolution=dimy,
                                             x_bounds=x_bounds,
                                             y_bounds=y_bounds)                

            # Keep numpy array of computational plane
            u_mesh = cut_plane.df.u.values.reshape(cut_plane.resolution[1],
                                                   cut_plane.resolution[0])
            t1 = time.time()
            # Get analytical model timing
            gauss_time = t1 - t0
            # Keep min value for plotting
            vmin = np.min(u_mesh)

        # Initialise model for evaluation
        model.eval()
        t0 = time.time()
        # Initialise neural output vector
        neural = np.zeros(dimx * dimy)

        # Normalise inputs
        speed_norm = (ws-smean)/sstd
        ti_norm = (ti - tmean)/tstd
        yw_norm = (yw - ymean)/ystd
        hbs_norm = (hb - hmean)/hstd

        # Make input tensor
        if inputs == 1:
            inpt = torch.tensor(([speed_norm]), dtype = torch.float)
        elif inputs == 2:
            inpt = torch.tensor(([speed_norm, ti_norm]), dtype = torch.float)
        elif inputs == 3:
            inpt = torch.tensor(([speed_norm, ti_norm, yw_norm]), dtype = torch.float)
        elif inputs == 4:
            inpt = torch.tensor(([speed_norm, ti_norm, yw_norm, hbs_norm]), dtype = torch.float)

        # Get DNN result as a 1D vector
        for ii in range(rows):
            neural[ii*out_piece:out_piece*(ii+1)] = self.forward(inpt, ii).detach().cpu().numpy()

        # Apply Filter to replace backround with u_stream (helps with scattering)
        if fltr < 1.0:
            neural[neural > ws*fltr] = ws

       
        if cubes == 1:
            # Compose 2D velocity deficit made of blocks

            dd = dim1*dim2
            jj = 0; ii = 0
            alpha = np.zeros((dimy, dimx))
            for k in range(int(dimx*dimy/(dim1*dim2))):

                alpha[ii:ii+dim1, jj:jj+dim2] = np.reshape(neural[k*dd:k*dd + dd], (dim1, dim2))

                jj += dim2
                if jj >= dimx:
                    jj = 0
                    ii += dim1

            neural = alpha.T

        else:
            if row_major == 0:
                # Compose 2D velocity deficit column-wise
                neural = np.reshape(neural, (dimx, dimy)).T
            else:
                # Compose 2D velocity deficit row-wise
                neural = np.reshape(neural, (dimy, dimx))

        t1 = time.time()
        # Get neural timing
        neural_time = t1 - t0


        #----------------- Plot wake deficit results -----------------#
        if timings == True or result_plots == True:

            if result_plots == True:
                # cmap = None
                # cmap = 'gnuplot'
                # cmap = 'viridis'
                cmap = 'coolwarm'

                sizeOfFont = 11
                fontProperties = {'family':'serif',
                    'weight' : 'normal', 'size' : sizeOfFont}

                fig, axs = plt.subplots(2)
                fig.suptitle('Velocities(m/s): Analytical (top), Neural (bot)')
                im1 = axs[0].imshow(u_mesh, vmin = vmin, cmap=cmap, extent=[x_bounds[0], x_bounds[1], y_bounds[0], y_bounds[1]])
                fig.colorbar(im1, ax = axs[0])

                # neural = np.kron(neural, np.ones((int(200/dim), int(200/dim))))
                im2 = axs[1].imshow(neural, vmin = vmin, interpolation=None, cmap=cmap, extent=[x_bounds[0], x_bounds[1], y_bounds[0], y_bounds[1]])
   
                fig.colorbar(im2, ax = axs[1])

                axs[1].set_xticklabels(axs[1].get_xticks().astype(int), fontProperties)
                axs[0].set_xticklabels(axs[0].get_xticks().astype(int), fontProperties)
                plt.show()

            max_val = np.max(u_mesh)

            if timings == True:
                absdifsum = np.sum(np.abs(u_mesh - neural))
                error = round(1/(dimx*dimy) * absdifsum/max_val * 100, 2)

                if result_plots == True:
                    print('Abs mean error (%): ', error)

            if result_plots == True:
                plt.imshow((np.abs(u_mesh - neural)/max_val*100), vmax=20, extent=[x_bounds[0], x_bounds[1], y_bounds[0], y_bounds[1]])
                plt.colorbar()
                plt.title('Abs difference')
                plt.show()

        final = np.copy(neural)

        # Replace current turbine inlet speed (ws) with farm u_stream (for superimposed wakes)
        final[final == ws] = u_stream
        if result_plots == 1:
            plt.imshow(final, extent=[x_bounds[0], x_bounds[1], y_bounds[0], y_bounds[1]])
            plt.show()

        if timings == True:
            return gauss_time, neural_time, error
        else:
            return final
