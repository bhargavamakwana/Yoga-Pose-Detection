# -*- coding: utf-8 -*-
"""DL_yoga-pose-detection.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/155pUpPtTuspLwCJRFRCsJhLYNz95Xyqp
"""

# Commented out IPython magic to ensure Python compatibility.
import numpy as np # linear algebra
import pandas as pd # data processing, CSV file I/O (e.g. pd.read_csv)
import os
import matplotlib.pyplot as plt

import torch
import torch.nn as nn
import torch.optim as optim
import torch.nn.functional as F
import torch.backends.cudnn as cudnn

import torchvision
import torchvision.transforms as transforms
import glob
import os
import argparse
import matplotlib.pyplot as plt

from torch.autograd import Variable
import torch.utils.data as data
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
import matplotlib.pyplot as plt


# %matplotlib inline
# %config InlineBackend.figure_format = 'retina'

TRAIN_DATA_PATH = '/scratch/bm3125/pytorch-example/Yoga-Pose-Detection/DATASET/TRAIN' #directory with training images
TEST_DATA_PATH = '/scratch/bm3125/pytorch-example/Yoga-Pose-Detection/DATASET/TEST' #directory with testing images

my_transform = transforms.Compose([
    transforms.Resize((224,224)),
    #transforms.RandomCrop(32, padding=4),
    transforms.RandomHorizontalFlip(),
    transforms.ToTensor(),
    transforms.Normalize((0.4914, 0.4822, 0.4465), (0.2023, 0.1994, 0.2010))
])


train_data = torchvision.datasets.ImageFolder(root=TRAIN_DATA_PATH, transform=my_transform)
train_data_loader = data.DataLoader(train_data, batch_size=16, shuffle=True,  num_workers=2)
test_data = torchvision.datasets.ImageFolder(root=TEST_DATA_PATH, transform=my_transform)
test_data_loader  = data.DataLoader(test_data, batch_size=16, shuffle=True, num_workers=2)

class NeuralNet(nn.Module):
  
    def __init__(self):
        super(NeuralNet, self).__init__()

        # spatial size: (224,224)    # number of channels = 3
        self.conv1 = nn.Conv2d(3, 64, kernel_size=(3,3), padding = 'same')
        self.pool1 = nn.MaxPool2d(2)
        self.drop1 = nn.Dropout(0.25)

        self.conv2 = nn.Conv2d(64, 128, kernel_size=(3,3), padding = 'same')
        self.pool2 = nn.MaxPool2d(2)
        self.drop2 = nn.Dropout(0.25)

        self.conv3 = nn.Conv2d(128,256, kernel_size=(3,3), padding = 'same')
        self.pool3 = nn.MaxPool2d(2)
        self.drop3 = nn.Dropout(0.25)

        self.linear4 = nn.Linear(256*28*28,1024)
        self.drop4 = nn.Dropout(0.5)

        self.linear5 = nn.Linear(1024,5)

        self.relu = nn.ReLU()
        self.softmax = nn.Softmax()
        
    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.pool1(x)
        x = self.drop1(x)
        
        x = self.relu(self.conv2(x))
        x = self.pool2(x)
        x = self.drop2(x)

        x = self.relu(self.conv3(x))
        x = self.pool3(x)
        x = self.drop3(x)
        
        x = x.view(-1, self.num_flat_features(x))
        x = self.relu(self.linear4(x))
        x = self.drop4(x)
        
        x = x.view(-1, self.num_flat_features(x))
        x = self.linear5(x)
        
        return x
      
    def num_flat_features(self, x):
        size = x.size()[1:]  # all dimensions except the batch dimension
        num_features = 1
        for s in size:
            num_features *= s
        return num_features
        
        
net = NeuralNet()

from torchsummary import summary
#summary(net, input_size=(3, 224, 224))

#####################################################################################
    # Select and Configure the device
#####################################################################################
    
device = 'cuda' if torch.cuda.is_available() else 'cpu'
net = net.to(device)
if device == 'cuda':
    net = torch.nn.DataParallel(net)
    cudnn.benchmark = True

optimizer = optim.SGD(net.parameters(), lr=0.0001, momentum=0.9, weight_decay=5e-4)
criterion = nn.CrossEntropyLoss()
scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=200)

epochs = 1  
batch_size = 16

def count_parameters(model):
    return sum(p.numel() for p in net.parameters() if p.requires_grad)
    # torch.numel() returns number of elements in a tensor
print(count_parameters(net))

from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

#####################################################################################
    # Initialize the variables
#####################################################################################  

best_acc = 0  # best test accuracy
start_epoch = 0  # start from epoch 0 or last checkpoint epoch
test_loss_list = [] # save the test loss for each epoch to plot
test_acc_list = [] # to save the test accuracy for each epoch to plot

train_loss_list = [] # to save the train loss for each epoch
train_acc_list = [] # to save the train accuracy for each epoch to plot

#history = model.fit(train_generator, epochs = epochs,validation_data = validation_generator)

#####################################################################################
    #Perform the Training and testing of the model
#####################################################################################
# Training
def train(epoch):
    global train_loss_list
    print('\nEpoch: %d' % epoch)
    net.train()
    train_loss = 0
    correct = 0
    total = 0
    for batch_idx, (inputs, targets) in enumerate(train_data_loader):
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()
        outputs = net(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()

        train_loss += loss.item()
        _, predicted = outputs.max(1)
        total += targets.size(0)
        correct += predicted.eq(targets).sum().item()


    train_loss_perEpoch = train_loss/(batch_idx+1)
    train_acc_perEpoch = 100.*correct/total
    train_loss_list.append(train_loss_perEpoch)
    train_acc_list.append(train_acc_perEpoch)
    print('Train Loss: %.3f | Acc: %.3f%% (%d/%d)'% (train_loss_perEpoch, train_acc_perEpoch, correct, total)  )


#####################################################################################
    
# Tesing
def test(epoch):
    global best_acc
    net.eval()
    test_loss = 0
    correct = 0
    total = 0
    with torch.no_grad():
        for batch_idx, (inputs, targets) in enumerate(test_data_loader):
            inputs, targets = inputs.to(device), targets.to(device)
            outputs = net(inputs)
            loss = criterion(outputs, targets)

            test_loss += loss.item()
            _, predicted = outputs.max(1)
            total += targets.size(0)
            correct += predicted.eq(targets).sum().item()


    # Save checkpoint.
    test_acc = 100.*correct/total
    test_loss_perEpoch = test_loss/(batch_idx+1)    
    test_acc_list.append(test_acc)
    test_loss_list.append(test_loss_perEpoch)
    if test_acc > best_acc:
        print('Saving..')
        print('Test Loss: %.3f | Acc: %.3f%% (%d/%d)'% (test_loss_perEpoch, test_acc, correct, total))
        print('#####################################################################################')
        
        #Save the state of the model, best accuracy yet and the current epoch
        state = {
            'net': net.state_dict(),
            'acc': test_acc,
            'epoch': epoch,
        }
        if not os.path.isdir('checkpoint'):
            os.mkdir('checkpoint')
        torch.save(state, './checkpoint/ckpt.pt')
        best_acc = test_acc

#####################################################################################
        # Call the Training and Testing functions 
        # based on the remaining number of epochs
#####################################################################################

for epoch in range(start_epoch, start_epoch+100):
    train(epoch)
    test(epoch)
    scheduler.step()

#####################################################################################

print('Best Accuracy of the model %.3f%%'% (best_acc))

plt.plot(train_loss_list)
plt.plot(test_loss_list)
plt.legend(["train", "val"])
plt.title("Loss")
plt.savefig("Last_Loss_4_4.jpg")

'''
train_loss, train_acc = model.evaluate(train_generator)
test_loss, test_acc   = model.evaluate(validation_generator)
print("final train accuracy = {:.2f} , validation accuracy = {:.2f}".format(train_acc*100, test_acc*100))
'''

'''
model.save('YogaNet_model_1_1.h5')
'''


"""The above prediction was correct."""

