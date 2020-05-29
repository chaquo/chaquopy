import unittest


class TestTorch(unittest.TestCase):

    # Based on https://pytorch.org/tutorials/beginner/pytorch_with_examples.html#pytorch-optim
    def test_basic(self):
        import torch

        # N is batch size; D_in is input dimension;
        # H is hidden dimension; D_out is output dimension.
        N, D_in, H, D_out = 64, 1000, 100, 10

        # Create random Tensors to hold inputs and outputs
        x = torch.randn(N, D_in)
        y = torch.randn(N, D_out)

        # Use the nn package to define our model and loss function.
        model = torch.nn.Sequential(
            torch.nn.Linear(D_in, H),
            torch.nn.ReLU(),
            torch.nn.Linear(H, D_out),
        )
        loss_fn = torch.nn.MSELoss(reduction='sum')

        # Use the optim package to define an Optimizer that will update the weights of
        # the model for us. Here we will use Adam; the optim package contains many other
        # optimization algoriths. The first argument to the Adam constructor tells the
        # optimizer which Tensors it should update.
        learning_rate = 1e-4
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

        def train():
            # Forward pass: compute predicted y by passing x to the model.
            y_pred = model(x)
            loss = loss_fn(y_pred, y)

            # Before the backward pass, use the optimizer object to zero all of the
            # gradients for the variables it will update (which are the learnable
            # weights of the model). This is because by default, gradients are
            # accumulated in buffers( i.e, not overwritten) whenever .backward()
            # is called. Checkout docs of torch.autograd.backward for more details.
            optimizer.zero_grad()

            # Backward pass: compute gradient of the loss with respect to model
            # parameters
            loss.backward()

            # Calling the step function on an Optimizer makes an update to its
            # parameters
            optimizer.step()

            return loss.item()

        for t in range(100):
            loss = train()
        self.assertGreater(loss, 10)
        for t in range(200):
            loss = train()
        self.assertLess(loss, 1)
