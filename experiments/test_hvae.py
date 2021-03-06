# %%

import sys
sys.path.append('../')

from utils.pseudo_inputs import PInputsData, PInputsGenerated, PseudoInputs
import models.hvae as hvae
import datetime
import tensorflow_probability as tfp
import tensorflow as tf
import numpy as np
import importlib
import matplotlib.pyplot as plt
import models.vae as vae
import tensorflow_datasets as tfds

tfk = tf.keras
tfkl = tfk.layers
tfpl = tfp.layers
tfd = tfp.distributions

# %% 
## Checking gpu setup
device_name = tf.test.gpu_device_name()
if device_name != '/device:GPU:0':
  print('GPU device not found')
print('Found GPU at: {}'.format(device_name))

# %%
# omniglot = tfds.load('omniglot', split = "train")
# ex = omniglot.take(1)
# for e in tfds.as_numpy(ex):
#   im = e['image']
#   print(im.shape)
#   im = im[:,:,0]
#   print(im.shape)
#   plt.imshow(im, cmap='Greys')
# %%
# x_train = tfds.load('omniglot', split = "train")
# x_train = np.array([x['image'][:,:,0] for x in tfds.as_numpy(x_train)]).astype(np.float32) / 255
# x_test = tfds.load('omniglot', split = "test")
# x_test = np.array([x['image'][:,:,0] for x in tfds.as_numpy(x_test)]).astype(np.float32) / 255
# x_train = x_train[:1000]
# %%
mnist = tf.keras.datasets.mnist

(x_train, y_train), (x_test, y_test) = mnist.load_data()
x_train = x_train.astype(np.float32) / 255
x_test = x_test.astype(np.float32) / 255
x_train = x_train[:1000]
# %%
x_train.shape
# %%
importlib.reload(hvae)
model = hvae.HVAE(original_dim = x_train.shape[1:], prior_type = vae.Prior.VAMPPRIOR, pseudo_inputs = PInputsData(x_train[:500]))
# model = hvae.HVAE(original_dim = x_train.shape[1:], prior_type = vae.Prior.STANDARD_GAUSSIAN)
model.prepare(learning_rate=0.0005)

#%%
# tfk.utils.plot_model(model, "my_model.png", show_shapes=True)

# %%
checkpoint_path = "../checkpoints/hvae/test.h5"
es_callback = tf.keras.callbacks.EarlyStopping(monitor='loss', patience=2)
cp_callback = tf.keras.callbacks.ModelCheckpoint(filepath=checkpoint_path,
                                                 save_weights_only=True,
                                                 verbose=1)
with tf.device('/device:GPU:0'):
    model.fit(x_train, x_train, epochs=1,
              batch_size=100, callbacks=[es_callback])
# %%
# checkpoint_path = "../checkpoints/hvae/test.h5"
# model.load_weights(checkpoint_path)
# %%
prior1, prior2 = model.get_priors()
encoder = model.get_encoder()
decoder = model.get_decoder()
# print(encoder.input)
# %%
#model.encoder(model.pseudo_inputs(None))[1]
prior2.sample()
# %%

generated_img = decoder.generate_img(prior2.sample(1)).mean()

plt.imshow(generated_img[0])

# %%
decoder.input_layer_z1.weights
# %%
# model.marginal_log_likelihood_one_sample(x_train[:2])

# %%
# model.marginal_log_likelihood_over_all_samples(x_train)
# %%
# Test Marginal Log-Likelihood (????)
reconst_test_dist = model(x_test)

ll = tf.reduce_mean(reconst_test_dist.log_prob(x_test))
ll
# %%
n_samples = 5
prior_samples = prior2.sample(n_samples)

posterior_dists_dependent = decoder.generate_img(prior_samples)
posterior_dists = tfd.Independent(decoder.generate_img(prior_samples), reinterpreted_batch_ndims=1)
print(posterior_dists_dependent)
print(posterior_dists)
ll = tf.reduce_mean(posterior_dists_dependent.log_prob(tf.reshape(x_test, (10000, 1, 28, 28))))
ll
# %%
