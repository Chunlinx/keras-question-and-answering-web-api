from keras.models import Model
from keras.layers.recurrent import LSTM
from keras.layers import Dense, Input, Embedding
from keras.preprocessing.sequence import pad_sequences
from collections import Counter
import nltk
import numpy as np
from sklearn.cross_validation import train_test_split

np.random.seed(42)

BATCH_SIZE = 64
NUM_EPOCHS = 2
HIDDEN_UNITS = 64
MAX_VOCAB_SIZE = 10000
DATA_PATH = 'data/cornell-dialogs/movie_lines_cleaned_10k.txt'

input_counter = Counter()
target_counter = Counter()

lines = open(DATA_PATH, 'rt', encoding='utf8').read().split('\n')
input_texts = []
target_texts = []
for idx, line in enumerate(lines):
    if idx % 2 == 0:
        input_texts.append(line)
    else:
        target_text = '[START] ' + line + ' [END]'
        target_texts.append(target_text)

for input_text, target_text in zip(input_texts, target_texts):
    input_words = [w.lower() for w in nltk.word_tokenize(input_text)]
    target_words = [w.lower() for w in nltk.word_tokenize(target_text)]
    for w in input_words:
        input_counter[w] += 1
    for w in target_words:
        target_counter[w] += 1

input_word2idx = dict()
target_word2idx = dict()
for idx, word in enumerate(input_counter.most_common(MAX_VOCAB_SIZE)):
    input_word2idx[word[0]] = idx + 2
for idx, word in enumerate(target_counter.most_common(MAX_VOCAB_SIZE)):
    target_word2idx[word[0]] = idx + 1

input_word2idx['[PAD]'] = 0
input_word2idx['[UNK]'] = 1
target_word2idx['[UNK]'] = 0

input_idx2word = {(idx, word) for word, idx in input_word2idx.items()}
target_idx2word = {(idx, word) for word, idx in target_word2idx.items()}

num_encoder_tokens = len(input_idx2word)
num_decoder_tokens = len(target_idx2word)

np.save('models/cornell/word-input-word2idx.npy', input_word2idx)
np.save('models/cornell/word-input-idx2word.npy', input_idx2word)
np.save('models/cornell/word-target-word2idx.npy', target_word2idx)
np.save('models/cornell/word-target-idx2word.npy', target_idx2word)

encoder_input_data = []

encoder_max_seq_length = 0
decoder_max_seq_length = 0

for input_text, target_text in zip(input_texts, target_texts):
    input_words = [w.lower() for w in nltk.word_tokenize(input_text)]
    target_words = [w.lower() for w in nltk.word_tokenize(target_text)]
    encoder_input_wids = []
    for w in input_words:
        w2idx = 1  # default [UNK]
        if w in input_word2idx:
            w2idx = input_word2idx[w]
        encoder_input_wids.append(w2idx)

    encoder_input_data.append(encoder_input_wids)
    encoder_max_seq_length = max(len(encoder_input_wids), encoder_max_seq_length)
    decoder_max_seq_length = max(len(target_words), decoder_max_seq_length)

context = dict()
context['num_encoder_tokens'] = num_encoder_tokens
context['num_decoder_tokens'] = num_decoder_tokens
context['encoder_max_seq_length'] = encoder_max_seq_length
context['decoder_max_seq_length'] = decoder_max_seq_length

print(context)
np.save('models/cornell/word-context.npy', context)


def generate_batch(input_text_data, output_text_data):
    num_batches = len(input_text_data) // BATCH_SIZE
    for batchIdx in range(0, num_batches - 1):
        start = batchIdx * BATCH_SIZE
        end = (batchIdx + 1) * BATCH_SIZE
        encoder_input_data_batch = pad_sequences(input_text_data[start:end], encoder_max_seq_length)
        decoder_target_data_batch = np.zeros(shape=(BATCH_SIZE, decoder_max_seq_length, num_decoder_tokens))
        decoder_input_data_batch = np.zeros(shape=(BATCH_SIZE, decoder_max_seq_length, num_decoder_tokens))
        for lineIdx, target_text in enumerate(output_text_data[start:end]):
            target_words = [w.lower() for w in nltk.word_tokenize(target_text)]
            for idx, w in enumerate(target_words):
                w2idx = 0  # default [UNK]
                if w in target_word2idx:
                    w2idx = target_word2idx[w]
                decoder_input_data_batch[lineIdx, idx, w2idx] = 1
                if idx > 0:
                    decoder_target_data_batch[lineIdx, idx - 1, w2idx] = 1
        yield [encoder_input_data_batch, decoder_input_data_batch], decoder_target_data_batch


encoder_inputs = Input(shape=(None,), name='encoder_inputs')
encoder_embedding = Embedding(input_dim=num_encoder_tokens, output_dim=HIDDEN_UNITS,
                              input_length=encoder_max_seq_length, name='encoder_embedding')
encoder_lstm = LSTM(units=HIDDEN_UNITS, return_state=True, name='encoder_lstm')
encoder_outputs, encoder_state_h, encoder_state_c = encoder_lstm(encoder_embedding(encoder_inputs))
encoder_states = [encoder_state_h, encoder_state_c]

decoder_inputs = Input(shape=(None, num_decoder_tokens), name='decoder_inputs')
decoder_lstm = LSTM(units=HIDDEN_UNITS, return_state=True, return_sequences=True, name='decoder_lstm')
decoder_outputs, decoder_state_h, decoder_state_c = decoder_lstm(decoder_inputs,
                                                                 initial_state=encoder_states)
decoder_dense = Dense(units=num_decoder_tokens, activation='softmax', name='decoder_dense')
decoder_outputs = decoder_dense(decoder_outputs)

model = Model([encoder_inputs, decoder_inputs], decoder_outputs)

model.compile(loss='categorical_crossentropy', optimizer='rmsprop')

Xtrain, Xtest, Ytrain, Ytest = train_test_split(input_texts, target_texts, test_size=0.2, random_state=42)

train_gen = generate_batch(Xtrain, Ytrain)
test_gen = generate_batch(Xtest, Ytest)

train_num_batches = len(Xtrain) // BATCH_SIZE
test_num_batches = len(Xtest) // BATCH_SIZE

model.fit_generator(generator=train_gen, steps_per_epoch=train_num_batches,
                    epochs=NUM_EPOCHS,
                    verbose=1, validation_data=test_gen, validation_steps=test_num_batches)

json = model.to_json()
open('models/cornell/word-architecture.json', 'w').write(json)
model.save_weights('models/cornell/word-weights.h5')
