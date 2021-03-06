import sys
sys.path.append('../')

import os
import numpy as np
import pandas as pd
from utils.pseudo_inputs import PInputsData, PInputsGenerated
from utils.datasets import DatasetKey, get_dataset
import models.vanilla_vae as vanilla_vae
import models.vae as vae
import tensorflow as tf
import models.hvae as hvae
from enum import Enum

Dataset = DatasetKey


class Architecture(Enum):
    VANILLA = 0
    HVAE = 1


class PriorConfiguration(Enum):
    SG = 0
    VAMPDATA = 1
    VAMPGEN = 2


dataset_key_dict = {
    DatasetKey.MNIST: "MNIST",
    DatasetKey.OMNIGLOT: "OMNIGLOT",
    DatasetKey.CALTECH: "CALTECH"
}
architecture_key_dict = {
    Architecture.VANILLA: "VANILLA",
    Architecture.HVAE: "HVAE"
}
prior_key_dict = {
    PriorConfiguration.SG: "SG",
    PriorConfiguration.VAMPDATA: "VAMPDATA",
    PriorConfiguration.VAMPGEN: "VAMPGEN"
}


def get_checkpoint_path(dataset_key, architecture, prior_configuration, n_epochs=2000, root=".."):
    name = "{root_dir}/{dataset}_{model}_{prior}_{n_epochs}.cpkt".format(
        root_dir="{root}/checkpoints".format(root=root),
        dataset=dataset_key_dict[dataset_key],
        model=architecture_key_dict[architecture],
        prior=prior_key_dict[prior_configuration],
        n_epochs=n_epochs
    )
    return name


def get_history_path(dataset_key, architecture, prior_configuration, n_epochs=2000, root=".."):
    name = "{root_dir}/{dataset}_{model}_{prior}_{n_epochs}.csv".format(
        root_dir="{root}/history".format(root=root),
        dataset=dataset_key_dict[dataset_key],
        model=architecture_key_dict[architecture],
        prior=prior_key_dict[prior_configuration],
        n_epochs=n_epochs
    )
    return name


class Runner():
    n_pseudo_inputs = 500
    learning_rate = 0.001
    pseudo_inputs = None

    def __init__(
        self,
        dataset_key: DatasetKey,
        architecture: Architecture,
        prior_configuration: PriorConfiguration,
        n_epochs=2000,
        root = "..",
        learning_rate = 0.001
    ):
        self.dataset_key = dataset_key
        self.architecture = architecture
        self.prior_configuration = prior_configuration
        self.n_epochs = n_epochs
        self.learning_rate = learning_rate
        self.checkpoint_path = get_checkpoint_path(
            dataset_key=dataset_key,
            architecture=architecture,
            prior_configuration=prior_configuration,
            n_epochs=n_epochs,
            root = root
        )
        self.history_path = get_history_path(
            dataset_key=self.dataset_key,
            architecture=self.architecture,
            prior_configuration=self.prior_configuration,
            n_epochs=n_epochs,
            root = root
        )

    def fetch_dataset(self):
        (self.x_train, self.x_test) = get_dataset(self.dataset_key)

    def prepare_model(self):
        if self.dataset_key == DatasetKey.OMNIGLOT:
            self.n_pseudo_inputs = 1000
        if self.prior_configuration != PriorConfiguration.SG:
            self.prior_type = vae.Prior.VAMPPRIOR
            if self.prior_configuration == PriorConfiguration.VAMPDATA:
                self.pseudo_inputs = PInputsData(
                    pseudo_inputs=self.x_train[:self.n_pseudo_inputs])
            else:
                self.pseudo_inputs = PInputsGenerated(
                    original_dim=self.x_train.shape[1:], n_pseudo_inputs=self.n_pseudo_inputs)
        else:
            self.prior_type = vae.Prior.STANDARD_GAUSSIAN

        self.model_class = vanilla_vae.VanillaVAE if self.architecture == Architecture.VANILLA else hvae.HVAE
        self.model = self.model_class(
            original_dim=self.x_train.shape[1:], prior_type=self.prior_type, pseudo_inputs=self.pseudo_inputs)
        self.model.prepare(learning_rate=self.learning_rate)

    def reload_if_possible(self):
        if not os.path.isfile(self.history_path):
            return  # no history stored for this model
        history_losses = pd.read_csv(self.history_path, names=[
                                     "epoch", "loss", "val_loss"])
        number_epochs_done = history_losses.shape[0]
        if number_epochs_done != 0:
            # relink all layers
            one_input_size = [1] + list(self.x_train.shape[1:])
            self.model(np.zeros(one_input_size))

            self.model.load_weights(self.checkpoint_path)
            self.n_epochs -= number_epochs_done

    def run(self):
        self.fetch_dataset()
        self.prepare_model()
        self.reload_if_possible()
        # es_callback = tf.keras.callbacks.EarlyStopping(monitor='val_loss',
        #                                                min_delta=0.001,
        #                                                patience=50,
        #                                                verbose=1,
        #                                                restore_best_weights=True)
        cp_callback = tf.keras.callbacks.ModelCheckpoint(filepath=self.checkpoint_path,
                                                         save_weights_only=True,
                                                         monitor='val_loss',
                                                         verbose=1)
        csv_logger = tf.keras.callbacks.CSVLogger(
            self.history_path, append=True)

        if self.n_epochs <= 0:
            print(
                "This model has already been trained and stored for the required number of epochs.")
            print("Delete the file under {history} if you want to retrain.".format(
                history=self.history_path))
        self.model.fit(self.x_train, self.x_train, epochs=self.n_epochs,
                       validation_data=(self.x_test, self.x_test), batch_size=100, callbacks=[cp_callback, csv_logger])

    # To be used after training
    def reload_existing_model(self):
        self.fetch_dataset()
        self.prepare_model()
        self.reload_if_possible()
        self.full_history = pd.read_csv(self.history_path)
        return (self.model, self.full_history)
