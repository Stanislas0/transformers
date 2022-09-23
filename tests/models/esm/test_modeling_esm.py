# coding=utf-8
# Copyright 2022 The HuggingFace Inc. team. All rights reserved.
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
""" Testing suite for the PyTorch ESM model. """


import unittest

from transformers import EsmConfig, is_torch_available
from transformers.testing_utils import TestCasePlus, require_torch, slow, torch_device

from ...generation.test_generation_utils import GenerationTesterMixin
from ...test_configuration_common import ConfigTester
from ...test_modeling_common import ModelTesterMixin, ids_tensor, random_attention_mask


if is_torch_available():
    import torch

    from transformers import (
        EsmForCausalLM,
        EsmForMaskedLM,
        EsmForSequenceClassification,
        EsmForTokenClassification,
        EsmModel,
    )
    from transformers.models.esm.modeling_esm import (
        ESM_PRETRAINED_MODEL_ARCHIVE_LIST,
        EsmEmbeddings,
        create_position_ids_from_input_ids,
    )


# copied from tests.test_modeling_roberta
class EsmModelTester:
    def __init__(
        self,
        parent,
    ):
        self.parent = parent
        self.batch_size = 13
        self.seq_length = 7
        self.is_training = False
        self.use_input_mask = True
        self.use_token_type_ids = False
        self.use_labels = True
        self.vocab_size = 99
        self.hidden_size = 32
        self.num_hidden_layers = 5
        self.num_attention_heads = 4
        self.intermediate_size = 37
        self.hidden_act = "gelu"
        self.hidden_dropout_prob = 0.1
        self.attention_probs_dropout_prob = 0.1
        self.max_position_embeddings = 512
        self.type_vocab_size = 16
        self.type_sequence_label_size = 2
        self.initializer_range = 0.02
        self.num_labels = 3
        self.num_choices = 4
        self.scope = None

    def prepare_config_and_inputs(self):
        input_ids = ids_tensor([self.batch_size, self.seq_length], self.vocab_size)

        input_mask = None
        if self.use_input_mask:
            input_mask = random_attention_mask([self.batch_size, self.seq_length])

        sequence_labels = None
        token_labels = None
        choice_labels = None
        if self.use_labels:
            sequence_labels = ids_tensor([self.batch_size], self.type_sequence_label_size)
            token_labels = ids_tensor([self.batch_size, self.seq_length], self.num_labels)
            choice_labels = ids_tensor([self.batch_size], self.num_choices)

        config = self.get_config()

        return config, input_ids, input_mask, sequence_labels, token_labels, choice_labels

    def get_config(self):
        return EsmConfig(
            vocab_size=self.vocab_size,
            hidden_size=self.hidden_size,
            num_hidden_layers=self.num_hidden_layers,
            num_attention_heads=self.num_attention_heads,
            intermediate_size=self.intermediate_size,
            hidden_act=self.hidden_act,
            hidden_dropout_prob=self.hidden_dropout_prob,
            attention_probs_dropout_prob=self.attention_probs_dropout_prob,
            max_position_embeddings=self.max_position_embeddings,
            type_vocab_size=self.type_vocab_size,
            initializer_range=self.initializer_range,
        )

    def create_and_check_model(self, config, input_ids, input_mask, sequence_labels, token_labels, choice_labels):
        model = EsmModel(config=config)
        model.to(torch_device)
        model.eval()
        result = model(input_ids, attention_mask=input_mask)
        result = model(input_ids)
        result = model(input_ids)

        self.parent.assertEqual(result.last_hidden_state.shape, (self.batch_size, self.seq_length, self.hidden_size))
        self.parent.assertEqual(result.pooler_output.shape, (self.batch_size, self.hidden_size))

    def create_and_check_for_causal_lm(
        self,
        config,
        input_ids,
        input_mask,
        sequence_labels,
        token_labels,
        choice_labels,
        encoder_hidden_states,
        encoder_attention_mask,
    ):
        model = EsmForCausalLM(config=config)
        model.to(torch_device)
        model.eval()
        result = model(input_ids, attention_mask=input_mask, labels=token_labels)
        self.parent.assertEqual(result.logits.shape, (self.batch_size, self.seq_length, self.vocab_size))

    def create_and_check_for_masked_lm(
        self, config, input_ids, input_mask, sequence_labels, token_labels, choice_labels
    ):
        model = EsmForMaskedLM(config=config)
        model.to(torch_device)
        model.eval()
        result = model(input_ids, attention_mask=input_mask, labels=token_labels)
        self.parent.assertEqual(result.logits.shape, (self.batch_size, self.seq_length, self.vocab_size))

    def create_and_check_for_token_classification(
        self, config, input_ids, input_mask, sequence_labels, token_labels, choice_labels
    ):
        config.num_labels = self.num_labels
        model = EsmForTokenClassification(config=config)
        model.to(torch_device)
        model.eval()
        result = model(input_ids, attention_mask=input_mask, labels=token_labels)
        self.parent.assertEqual(result.logits.shape, (self.batch_size, self.seq_length, self.num_labels))

    def prepare_config_and_inputs_for_common(self):
        config_and_inputs = self.prepare_config_and_inputs()
        (
            config,
            input_ids,
            input_mask,
            sequence_labels,
            token_labels,
            choice_labels,
        ) = config_and_inputs
        inputs_dict = {"input_ids": input_ids, "attention_mask": input_mask}
        return config, inputs_dict


@require_torch
class EsmModelTest(ModelTesterMixin, GenerationTesterMixin, unittest.TestCase):

    all_model_classes = (
        (
            EsmForCausalLM,
            EsmForMaskedLM,
            EsmModel,
            EsmForSequenceClassification,
            EsmForTokenClassification,
        )
        if is_torch_available()
        else ()
    )
    all_generative_model_classes = (EsmForCausalLM,) if is_torch_available() else ()
    test_sequence_classification_problem_types = True

    def setUp(self):
        self.model_tester = EsmModelTester(self)
        self.config_tester = ConfigTester(self, config_class=EsmConfig, hidden_size=37)

    def test_config(self):
        self.config_tester.run_common_tests()

    def test_model(self):
        config_and_inputs = self.model_tester.prepare_config_and_inputs()
        self.model_tester.create_and_check_model(*config_and_inputs)

    def test_model_various_embeddings(self):
        config_and_inputs = self.model_tester.prepare_config_and_inputs()
        for type in ["absolute", "relative_key", "relative_key_query"]:
            config_and_inputs[0].position_embedding_type = type
            self.model_tester.create_and_check_model(*config_and_inputs)

    def test_for_masked_lm(self):
        config_and_inputs = self.model_tester.prepare_config_and_inputs()
        self.model_tester.create_and_check_for_masked_lm(*config_and_inputs)

    def test_for_token_classification(self):
        config_and_inputs = self.model_tester.prepare_config_and_inputs()
        self.model_tester.create_and_check_for_token_classification(*config_and_inputs)

    @slow
    def test_model_from_pretrained(self):
        for model_name in ESM_PRETRAINED_MODEL_ARCHIVE_LIST[:1]:
            model = EsmModel.from_pretrained(model_name)
            self.assertIsNotNone(model)

    def test_create_position_ids_respects_padding_index(self):
        """Ensure that the default position ids only assign a sequential . This is a regression
        test for https://github.com/huggingface/transformers/issues/1761

        The position ids should be masked with the embedding object's padding index. Therefore, the
        first available non-padding position index is EsmEmbeddings.padding_idx + 1
        """
        config = self.model_tester.prepare_config_and_inputs()[0]
        model = EsmEmbeddings(config=config)

        input_ids = torch.as_tensor([[12, 31, 13, model.padding_idx]])
        expected_positions = torch.as_tensor(
            [[0 + model.padding_idx + 1, 1 + model.padding_idx + 1, 2 + model.padding_idx + 1, model.padding_idx]]
        )

        position_ids = create_position_ids_from_input_ids(input_ids, model.padding_idx)
        self.assertEqual(position_ids.shape, expected_positions.shape)
        self.assertTrue(torch.all(torch.eq(position_ids, expected_positions)))

    def test_create_position_ids_from_inputs_embeds(self):
        """Ensure that the default position ids only assign a sequential . This is a regression
        test for https://github.com/huggingface/transformers/issues/1761

        The position ids should be masked with the embedding object's padding index. Therefore, the
        first available non-padding position index is EsmEmbeddings.padding_idx + 1
        """
        config = self.model_tester.prepare_config_and_inputs()[0]
        embeddings = EsmEmbeddings(config=config)

        inputs_embeds = torch.empty(2, 4, 30)
        expected_single_positions = [
            0 + embeddings.padding_idx + 1,
            1 + embeddings.padding_idx + 1,
            2 + embeddings.padding_idx + 1,
            3 + embeddings.padding_idx + 1,
        ]
        expected_positions = torch.as_tensor([expected_single_positions, expected_single_positions])
        position_ids = embeddings.create_position_ids_from_inputs_embeds(inputs_embeds)
        self.assertEqual(position_ids.shape, expected_positions.shape)
        self.assertTrue(torch.all(torch.eq(position_ids, expected_positions)))


@require_torch
class EsmModelIntegrationTest(TestCasePlus):
    @slow
    def test_inference_masked_lm(self):
        model = EsmForMaskedLM.from_pretrained("Rocketknight1/esm-2-8m")
        input_ids = torch.tensor([[0, 1, 2, 3, 4, 5]])
        output = model(input_ids)[0]

        vocab_size = 33

        expected_shape = torch.Size((1, 6, vocab_size))
        self.assertEqual(output.shape, expected_shape)

        expected_slice = torch.tensor(
            [[[[24.4653, -8.0736, 10.0146], [-9.0505, -15.9262, -4.8583], [-6.9496, -14.6652, 6.2619]]]]
        )

        self.assertTrue(torch.allclose(output[:, :3, :3], expected_slice, atol=1e-4))

    @slow
    def test_inference_no_head(self):
        model = EsmModel.from_pretrained("Rocketknight1/esm-2-8m")

        input_ids = torch.tensor([[0, 6, 4, 13, 5, 4, 16, 12, 11, 7, 2]])
        output = model(input_ids)[0]
        # compare the actual values for a slice.
        expected_slice = torch.tensor(
            [[[-0.1687, 0.0673, 0.0991], [0.2569, 0.0041, 0.2266], [0.1488, 0.0387, 0.0665]]]
        )

        self.assertTrue(torch.allclose(output[:, :3, :3], expected_slice, atol=1e-4))

    # XXX: this might be a candidate for common tests if we have many of those
    def test_lm_head_ignore_keys(self):
        from copy import deepcopy

        keys_to_ignore_on_save_tied = [r"lm_head.decoder.weight", r"lm_head.decoder.bias"]
        keys_to_ignore_on_save_untied = [r"lm_head.decoder.bias"]
        config = EsmConfig.from_pretrained("Rocketknight1/esm-2-8m")
        config_tied = deepcopy(config)
        config_tied.tie_word_embeddings = True
        config_untied = deepcopy(config)
        config_untied.tie_word_embeddings = False
        for cls in [EsmForMaskedLM, EsmForCausalLM]:
            model = cls(config_tied)
            self.assertEqual(model._keys_to_ignore_on_save, keys_to_ignore_on_save_tied, cls)

            # the keys should be different when embeddings aren't tied
            model = cls(config_untied)
            self.assertEqual(model._keys_to_ignore_on_save, keys_to_ignore_on_save_untied, cls)

            # test that saving works with updated ignore keys - just testing that it doesn't fail
            model.save_pretrained(self.get_auto_remove_tmp_dir())
