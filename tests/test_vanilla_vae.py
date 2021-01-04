# %%
"""
The following is for resolving paths for windows users 
(pretty sure linux handles it better)
Feel free to comment them out :)
"""
import sys
sys.path.append('../')
import matplotlib.pyplot as plt
import importlib
import numpy as np
import tensorflow as tf
import tensorflow_probability as tfp
import datetime
import models.vanilla_vae as vae
import utils.evaluation as evaluation
from utils.pseudo_inputs import PInputsData, PInputsGenerated, PseudoInputs


tfk = tf.keras
tfkl = tfk.layers
tfpl = tfp.layers
tfd = tfp.distributions

# %%
# Checking gpu setup
device_name = tf.test.gpu_device_name()
if device_name != '/device:GPU:0':
    print('GPU device not found')
print('Found GPU at: {}'.format(device_name))

# %%
mnist = tf.keras.datasets.mnist

(x_train, y_train), (x_test, y_test) = mnist.load_data()
x_train = x_train.astype(np.float32) / 255
x_test = x_test.astype(np.float32) / 255
# %%
importlib.reload(vae)
model = vae.VariationalAutoEncoder(
    prior_type=vae.Prior.VAMPPRIOR, pseudo_inputs=PInputsData(x_train[:500]))

model.prepare()

# %%
checkpoint_path = "../checkpoints/vanilla_vae/test.h5"
es_callback = tf.keras.callbacks.EarlyStopping(monitor='loss', patience=2)
cp_callback = tf.keras.callbacks.ModelCheckpoint(filepath=checkpoint_path,
                                                 save_weights_only=True,
                                                 verbose=1)

metrics_callback = evaluation.MetricsCallback(x_train)
log_dir = "logs/fit/" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
tensorboard_callback = tf.keras.callbacks.TensorBoard(
    log_dir=log_dir, histogram_freq=1)
with tf.device('/device:GPU:0'):
    model.fit(x_train, x_train, epochs=2,
              batch_size=100, callbacks=[es_callback, cp_callback, metrics_callback, tensorboard_callback])

# %%
re = np.array(metrics_callback.re)
loss = model.history.history["loss"]
kl = loss - re
plt.plot(re, label="re")
plt.plot(loss, label="loss")
plt.plot(kl, label="kl")
plt.legend()
plt.show()

# %%
prior = model.get_prior()
encoder = model.get_encoder()
decoder = model.get_decoder()
generated_img = decoder(prior.sample(1)).mean()

plt.imshow(generated_img[0])

# %%
# Only of interest if using vampprior
im_pseudo = np.reshape(model.pseudo_inputs(None), (500, 28, 28))
plt.imshow(im_pseudo[np.random.randint(0, 500)])
# %%
# Test Marginal Log-Likelihood (????)
reconst_test_dist = model(x_test)

ll = tf.reduce_mean(reconst_test_dist.log_prob(x_test))
ll
# %%
n_samples = 20
prior_samples = prior.sample(n_samples)

posterior_dists_dependent = decoder(prior_samples)
posterior_dists = tfd.Independent(
    decoder(prior_samples), reinterpreted_batch_ndims=1)
print(posterior_dists_dependent)
print(posterior_dists)
ll = tf.reduce_mean(posterior_dists_dependent.log_prob(
    tf.reshape(x_test, (10000, 1, 28, 28))))
ll
# %%
