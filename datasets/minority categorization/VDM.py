import numpy as np 


class VDM():
    def __init__(self, X, y_ix, cat_ix):
        """ Value Difference Metric
        Distance metric class which initializes the parameters
        used in vdm() function
        
        Parameters
        ----------
        X : array-like of shape = [n_rows, n_features]
            First instance 
            
        y_ix : int array-like, list of shape [1]
            Single element array with indices for categorical output variable
            If y is numerical it should be converted to categorical (if it makes sense)
        
        cat_ix : array-like of shape = [cat_columns_number]
            List containing categorical feature indices
    
        Returns
        -------
        None
        """           
        self.cat_ix = cat_ix
        self.col_ix = [i for i in range(X.shape[1])]
        self.y_ix = y_ix
        self.classes = np.unique(X.loc[:, y_ix])
        self.unique_value_index = {}
        
        array_len = 0
        # Get the max no. of unique classes within columns to initialize the array
        for ix in self.cat_ix:
            max_val = len(np.unique(X.loc[:, ix]))
            if max_val > array_len:
                array_len = max_val

        # Store the list of unique classes elements for each categorical column
        # self.col_ix is used here for clearer indices assignment
        self.unique_attributes = np.full((array_len, len(self.col_ix)), fill_value=-1)
        for ix in self.cat_ix:

            unique_vals = np.unique(X.loc[:, ix])
            self.unique_value_index[ix] = unique_vals
            self.unique_attributes[0:len(unique_vals), ix] = range(len(unique_vals))



        # Declare the 3D numpy array which holds specifc count for each attribute
        # for each column for each output class
        # +1 in len(self.classes) + 1 is to store the sum (N_a,x) in the last element
        self.final_count = np.zeros((len(self.col_ix), self.unique_attributes.shape[0], len(self.classes) + 1))
        # For each column
        for i, col in enumerate(self.cat_ix):
            # For each attribute value in the column
            for attr_idx in self.unique_attributes[:, col]:
                # If attribute exists
                if attr_idx != -1:
                    # For each output class value
                    for k, val in enumerate(self.classes):
                        # Get an attribute count for each output class
                        attr = self.unique_value_index[col][attr_idx]

                        row_ixs = list(X.index[X[col] == attr])
                        cnt = np.sum(X.loc[row_ixs, y_ix] == val)

                        self.final_count[col, attr_idx, k] = cnt
                    # Get a sum of all occurences
                    self.final_count[col, attr_idx, -1] = np.sum(self.final_count[col, attr_idx, :])


    def vdm(self, x, y):
        """ Value Difference Metric
        Distance metric function which calculates the distance
        between two instances. Handles heterogeneous data and missing values.
        For categorical variables, it uses conditional probability 
        that the output class is given 'c' when attribute 'a' has a value of 'n'.
        It can be used as a custom defined function for distance metrics
        in Scikit-Learn
        Parameters
        ----------
        x : array-like of shape = [n_features]
            First instance 
            
        y : array-like of shape = [n_features]
            Second instance
        Returns
        -------
        result: float
            Returns the result of the distance metrics function
        """
        result = np.zeros(len(x))

        for i in self.cat_ix:
            # Get indices to access the final_count array 
            x_ix = np.argwhere(self.unique_value_index[i] == x[i]).flatten()
            y_ix = np.argwhere(self.unique_value_index[i] == y[i]).flatten()

            # Get the count to calculate the conditional probability
            N_ax = self.final_count[i, x_ix, -1].flatten()
            N_ay = self.final_count[i, y_ix, -1].flatten()

            N_axc = self.final_count[i, x_ix].flatten()
            N_ayc = self.final_count[i, y_ix].flatten()
            if N_ax != 0 and N_ay != 0:
                temp_result = abs(N_axc/N_ax - N_ayc/N_ay)
                temp_result = np.sum(temp_result)
                result[i] = temp_result
            else:
                print("Division by zero is not allowed!")

        return result
    