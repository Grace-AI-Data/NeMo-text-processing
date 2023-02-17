# Copyright (c) 2021, NVIDIA CORPORATION.  All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from argparse import ArgumentParser

from nemo_text_processing.inverse_text_normalization.inverse_normalize import InverseNormalizer
from nemo_text_processing.text_normalization.data_loader_utils import (
    evaluate,
    known_types,
    load_files,
    training_data_to_sentences,
    training_data_to_tokens,
)


'''
Runs Evaluation on data in the format of : <semiotic class>\t<unnormalized text>\t<`self` if trivial class or normalized text>
like the Google text normalization data https://www.kaggle.com/richardwilliamsproat/text-normalization-for-english-russian-and-polish
'''


def parse_args():
    parser = ArgumentParser()
    parser.add_argument("--input", help="input file path", type=str)
    parser.add_argument(
        "--lang", help="language", choices=['en', 'de', 'es', 'pt', 'ru', 'fr', 'vi'], default="en", type=str
    )
    parser.add_argument(
        "--cat",
        dest="category",
        help="focus on class only (" + ", ".join(known_types) + ")",
        type=str,
        default=None,
        choices=known_types,
    )
    parser.add_argument("--filter", action='store_true', help="clean data for inverse normalization purposes")
    return parser.parse_args()


if __name__ == "__main__":
    # Example usage:
    # python run_evaluate.py --input=<INPUT> --cat=<CATEGORY> --filter
    args = parse_args()
    if args.lang == 'en':
        from nemo_text_processing.inverse_text_normalization.en.clean_eval_data import filter_loaded_data
    file_path = args.input
    inverse_normalizer = InverseNormalizer()

    print(f"Loading training data: {file_path}")
    training_data = load_files([file_path])

    if args.filter:
        training_data = filter_loaded_data(training_data)

    if args.category is None:
        print("Sentence level evaluation...")
        sentences_un_normalized, sentences_normalized, _ = training_data_to_sentences(training_data)
        print(f"- Data: {len(sentences_normalized)} sentences")
        sentences_prediction = inverse_normalizer.inverse_normalize_list(sentences_normalized)
        print("- Denormalized. Evaluating...")
        sentences_accuracy = evaluate(
            preds=sentences_prediction, labels=sentences_un_normalized, input=sentences_normalized
        )
        print(f"- Accuracy: {str(sentences_accuracy)}")

    print("Token level evaluation...")
    tokens_per_type = training_data_to_tokens(training_data, category=args.category)
    token_accuracy = {}
    for token_type in tokens_per_type:
        print(f"- Token type: {token_type}")
        tokens_un_normalized, tokens_normalized = tokens_per_type[token_type]
        print(f"  - Data: {len(tokens_normalized)} tokens")
        tokens_prediction = inverse_normalizer.inverse_normalize_list(tokens_normalized)
        print("  - Denormalized. Evaluating...")
        token_accuracy[token_type] = evaluate(tokens_prediction, tokens_un_normalized, input=tokens_normalized)
        print(f"  - Accuracy: {str(token_accuracy[token_type])}")
    token_count_per_type = {token_type: len(tokens_per_type[token_type][0]) for token_type in tokens_per_type}
    token_weighted_accuracy = [
        token_count_per_type[token_type] * accuracy for token_type, accuracy in token_accuracy.items()
    ]
    print(
        f"- Accuracy: {str(sum(token_weighted_accuracy) / sum(token_count_per_type.values()))}"
    )

    print(f" - Total: {str(sum(token_count_per_type.values()))}", '\n')

    for token_type in token_accuracy:
        if token_type not in known_types:
            raise ValueError(f"Unexpected token type: {token_type}")

    if args.category is None:
        c1 = ['Class', 'sent level'] + known_types
        c2 = ['Num Tokens', len(sentences_normalized)] + [
            token_count_per_type[known_type] if known_type in tokens_per_type else '0' for known_type in known_types
        ]
        c3 = ["Denormalization", sentences_accuracy] + [
            token_accuracy.get(known_type, '0') for known_type in known_types
        ]

        for i in range(len(c1)):
            print(f'{str(c1[i]):10s} | {str(c2[i]):10s} | {str(c3[i]):5s}')
    else:
        print(f'numbers\t{token_count_per_type[args.category]}')
        print(f'Denormalization\t{token_accuracy[args.category]}')
