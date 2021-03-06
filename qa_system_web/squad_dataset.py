import json
import nltk
from qa_system_web.text_utils import in_white_list

DATA_PATH = '../qa_system_train/data/SQuAD/train-v1.1.json'
MAX_CONTEXT_SEQ_LENGTH = 300
MAX_QUESTION_SEQ_LENGTH = 60
MAX_TARGET_SEQ_LENGTH = 50
MAX_VOCAB_SIZE = 5000
MAX_DATA_COUNT = 5000


class SquADDataSet(object):
    data = None

    def __init__(self):
        self.data = []

        with open(DATA_PATH) as file:
            json_data = json.load(file)

            for instance in json_data['data']:
                for paragraph in instance['paragraphs']:
                    context = paragraph['context']
                    context_wids = [w.lower() for w in nltk.word_tokenize(context) if in_white_list(w)]
                    if len(context_wids) > MAX_CONTEXT_SEQ_LENGTH:
                        continue
                    qas = paragraph['qas']
                    for qas_instance in qas:
                        question = qas_instance['question']
                        question_wids = [w.lower() for w in nltk.word_tokenize(question) if in_white_list(w)]
                        if len(question_wids) > MAX_QUESTION_SEQ_LENGTH:
                            continue
                        answers = qas_instance['answers']
                        for answer in answers:
                            ans = answer['text']
                            answer_wids = [w.lower() for w in nltk.word_tokenize(ans) if in_white_list(w)]
                            if len(answer_wids) > MAX_TARGET_SEQ_LENGTH:
                                continue
                            if len(self.data) < MAX_DATA_COUNT:
                                self.data.append((context, question, ans))

                    if len(self.data) >= MAX_DATA_COUNT:
                        break

                if len(self.data) >= MAX_DATA_COUNT:
                    break

    def get_data(self, index):
        return self.data[index]

    def size(self):
        return len(self.data)


def main():
    ds = SquADDataSet()
    print(ds.get_data(2))


if __name__ == '__main__':
    main()
