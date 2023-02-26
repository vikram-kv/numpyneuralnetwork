from helper_functions import *
import numpy as np
import time

class NeuralNetwork:
    def __init__(self, args, num_classes, in_dim):
        self.hlayercount = args.num_hidden_layers
        self.act_fn = [args.act_func for _ in range(self.hlayercount+1)]
        self.hidden_sizes = [args.hidden_size for _ in range(self.hlayercount+1)]
        self.init_method = args.w_i
        self.weight_decay = args.w_d
        self.loss_fn = args.loss
        self.out_layer_size = num_classes
        self.in_layer_size = in_dim
        self.hidden_sizes[0] = in_dim # for ease later
        self.create_dicts()
        self.init_parameters()
        pass
    
    def create_dicts(self):
        self.weights = dict()
        self.biases = dict()

    # implement Xavier initialization
    def init_parameters(self):
        if self.init_method == 'Xavier':
            pass
        else:
            np.random.seed(42)
            for idx in range(1, self.hlayercount + 1):
                self.weights[idx] = np.random.randn(self.hidden_sizes[idx], self.hidden_sizes[idx - 1])
                self.biases[idx] = np.random.randn(self.hidden_sizes[idx])
            
            # for output layer
            outidx = self.hlayercount + 1
            self.weights[outidx] = np.random.randn(self.out_layer_size, self.hidden_sizes[outidx - 1])
            self.biases[outidx] = np.random.randn(self.out_layer_size)

    def forward(self, input : np.array, true_label):
        incopy = np.copy(input)
        outvalues, outderivs, actvalues = dict(), dict(), dict()
        outvalues[0] = incopy

        for idx in range(1, self.hlayercount + 1):
            l, m, n = forward_one_layer(self.weights, self.biases, idx, incopy, self.act_fn[idx])
            actvalues[idx], outvalues[idx], outderivs[idx] = l, m, n
            incopy = np.copy(m)
        
        # final layer - get act values and compute loss
        actvalues[self.hlayercount + 1], _, _ = forward_one_layer(self.weights, self.biases, self.hlayercount + 1, incopy, None)
        outvalues[self.hlayercount + 1] = safe_softmax(actvalues[self.hlayercount + 1])
        loss = calculate_loss(self.loss_fn, outvalues[self.hlayercount + 1], true_label)

        return outvalues, outderivs, loss

    def backward(self, true_label, outvalues, outderivs, weights):
        weight_gradients, bias_gradients = dict(), dict() # to be returned
        loss_grad_act_values = dict() # temporary within this function
        loss_grad_outputs = dict()

        final_layer_output = outvalues[self.hlayercount + 1]

        loss_grad_final_output = loss_grad_fl_outputs(self.loss_fn, final_layer_output, true_label)
        factor = np.dot(final_layer_output, loss_grad_final_output)
        loss_grad_act_values[self.hlayercount + 1] = np.multiply(final_layer_output, loss_grad_final_output) - factor * final_layer_output

        weight_gradients[self.hlayercount + 1]  = np.outer(loss_grad_act_values[self.hlayercount + 1], outvalues[self.hlayercount])
        bias_gradients[self.hlayercount + 1] = np.copy(loss_grad_act_values[self.hlayercount + 1])

        for idx in range(self.hlayercount, 0, -1):
            loss_grad_outputs[idx] = np.transpose(weights[idx + 1]) @ (loss_grad_act_values[idx+1])
            loss_grad_act_values[idx] = np.multiply(loss_grad_outputs[idx], outderivs[idx])
            weight_gradients[idx]  = np.outer(loss_grad_act_values[idx], outvalues[idx-1])
            bias_gradients[idx] = np.copy(loss_grad_act_values[idx])
        
        return weight_gradients, bias_gradients

    # need to include optimizers here onwards
    def update_parameters(self, learning_rate, agg_weight_changes, agg_bias_changes):
        eta = learning_rate
        for idx in range(1, self.hlayercount + 2):
            self.weights[idx] -= eta * agg_weight_changes[idx]
            self.biases[idx] -= eta * agg_bias_changes[idx]

    def refresh_aggregates(self):
        agg_weight_changes = dict()
        agg_biases_changes = dict()
        agg_loss = 0.0
        agg_correct = 0
        for idx in self.weights:
            agg_weight_changes[idx] = np.zeros(self.weights[idx].shape)
            agg_biases_changes[idx] = np.zeros(self.biases[idx].shape)
        return agg_weight_changes, agg_biases_changes, agg_loss, agg_correct

    def test(self, val_data):
        val_X, val_y = zip(*val_data)
        val_X = list(val_X); val_y = list(val_y)
        total_count = 0
        total_correct = 0
        total_loss = 0.0

        for X, y in zip(val_X, val_y):
            outvalues, outderivs, loss = self.forward(X, y)
            total_loss += loss
            y_pred = np.argmax(outvalues[self.hlayercount + 1])
            total_count += 1
            if (y == y_pred):
                total_correct += 1

        acc = total_correct / total_count
        print(f'accuracy = {acc}; loss = {total_loss}')
        return acc, total_loss
            
    # NOTE - ensure batch size divides total train data size
    def train(self, train_data, val_data, epochs, batchsize, learning_rate):
        train_X, train_y = zip(*train_data)
        train_X = list(train_X); train_y = list(train_y)

        for i in range(epochs):
            print(f'EPOCH - {i}')
            batch_count = 0
            num_samples = 0
            agg_weight_changes, agg_biases_changes, agg_loss, agg_crct = self.refresh_aggregates()
            for X, y in zip(train_X, train_y):
                outvalues, outderivs, loss = self.forward(X, y)
                y_pred = np.amax(outvalues[self.hlayercount + 1])
                weight_gradients, bias_gradients = self.backward(y, outvalues, outderivs, self.weights)
                num_samples += 1
                agg_loss += loss

                if (y_pred == y):
                    agg_crct += 1

                for idx in range(1, self.hlayercount + 2):
                    agg_weight_changes[idx] += weight_gradients[idx]
                    agg_biases_changes[idx] += bias_gradients[idx]

                if (num_samples % batchsize == 0):
                    # make log
                    self.update_parameters(learning_rate, agg_weight_changes, agg_biases_changes)
                    num_samples = 0
                    agg_weight_changes, agg_biases_changes, agg_loss, agg_crct = self.refresh_aggregates()
                    batch_count += 1
                    if (batch_count % 1000 == 0):
                        _, _ = self.test(val_data)
