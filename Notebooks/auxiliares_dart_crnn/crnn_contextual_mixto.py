"""Entrenamiento y predicción de la CRNN contextual de estadificación del sueño."""

import numpy as np
import pandas as pd
import tensorflow as tf
from scipy.special import softmax


def bloques(x, desfase, relleno=0):
    pad = [(desfase,-(len(x)+desfase)%15)] + [(0,0)]*(x.ndim-1)
    return np.pad(x,pad,constant_values=relleno).reshape(-1,15,*x.shape[1:])


def entrenar_crnn(filas, entradas, *, clases, desfases, semilla, epocas=15, al_terminar_epoca=None):
    """Entrena una red desde cero y permite observar el modelo tras cada época."""
    tf.keras.backend.clear_session()
    tf.keras.utils.set_random_seed(semilla)
    rng = np.random.default_rng(semilla)
    l = tf.keras.layers
    entrada = l.Input((15,6,96))
    z = l.TimeDistributed(l.Conv1D(48,3,padding='same',activation='relu'))(entrada)
    z = l.TimeDistributed(l.Flatten())(z)
    z = l.Dropout(.15)(l.Dense(48,activation='relu')(z))
    z = l.Bidirectional(l.GRU(32,return_sequences=True))(z)
    red = tf.keras.Model(entrada,l.Dense(5,activation='softmax')(l.Dropout(.20)(z)))
    red.compile(optimizer=tf.keras.optimizers.Adam(.001), loss='sparse_categorical_crossentropy')
    conteos = filas.etapa.value_counts().reindex(clases).to_numpy()
    pesos = (conteos.mean()/conteos)**.35
    pesos /= np.average(pesos,weights=conteos)
    lotes = {}
    for d in desfases:
        xs, ys = [], []
        for rid,g in filas.groupby('record_id'):
            y = np.full(len(entradas[rid]),-1,dtype='int32')
            y[g.epoch_index] = pd.Categorical(g.etapa,categories=clases).codes
            y = bloques(y,d,-1)
            valido = (y>=0).any(1)
            xs.append(bloques(entradas[rid],d)[valido])
            ys.append(y[valido])
        x,y = np.concatenate(xs),np.concatenate(ys)
        lotes[d] = (x,y.clip(0),np.where(y>=0,pesos[y.clip(0)],0).astype('float32'))
    for epoca in range(epocas):
        x,y,w = lotes[desfases[epoca%len(desfases)]]
        orden = rng.permutation(len(x))
        red.fit(x[orden], y[orden], sample_weight=w[orden], batch_size=64, epochs=1, shuffle=False, verbose=0)
        if al_terminar_epoca is not None:
            al_terminar_epoca(epoca + 1, red)
        if (epoca + 1) % 5 == 0 or epoca + 1 == epocas:
            print(f'CRNN · {epoca + 1}/{epocas} épocas', flush=True)
    return red

def prob_crnn(red, x, *, clases, desfases):
    vistas = []
    for d in desfases:
        v = red.predict(bloques(x,d),batch_size=128,verbose=0).reshape(-1,len(clases))
        vistas.append(v[d:d+len(x)].astype('float64'))
    return softmax(np.log(np.maximum(vistas,1e-10)).mean(axis=0),axis=1)
