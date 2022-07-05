import os, sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))

from torchvision.models.vision_transformer import (
    vit_b_16,
    vit_b_32,
    vit_l_16,
    vit_l_32,
    vit_h_14,
)

#
from torchvision.models.alexnet import alexnet 
from torchvision.models.densenet import densenet121, densenet169, densenet201, densenet161
from torchvision.models.efficientnet import (
    efficientnet_b0,
    efficientnet_b1,
    efficientnet_b2,
    efficientnet_b3,
    efficientnet_b4,
    efficientnet_b5,
    efficientnet_b6,
    efficientnet_b7,
    efficientnet_v2_s,
    efficientnet_v2_m,
    efficientnet_v2_l,
)
from torchvision.models.googlenet import googlenet
from torchvision.models.inception import inception_v3
from torchvision.models.mnasnet import mnasnet0_5, mnasnet0_75, mnasnet1_0, mnasnet1_3
from torchvision.models.mobilenetv2 import mobilenet_v2
from torchvision.models.mobilenetv3 import mobilenet_v3_large, mobilenet_v3_small

from torchvision.models.regnet import (
    regnet_y_400mf,
    regnet_y_800mf,
    regnet_y_1_6gf,
    regnet_y_3_2gf,
    regnet_y_8gf,
    regnet_y_16gf,
    regnet_y_32gf,
    regnet_y_128gf,
    regnet_x_400mf,
    regnet_x_800mf,
    regnet_x_1_6gf,
    regnet_x_3_2gf,
    regnet_x_8gf,
    regnet_x_16gf,
    regnet_x_32gf,
)
from torchvision.models.resnet import (
    resnet18,
    resnet34,
    resnet50,
    resnet101,
    resnet152,
    resnext50_32x4d,
    resnext101_32x8d,
    wide_resnet50_2,
    wide_resnet101_2,
)
from torchvision.models.segmentation import (
    fcn_resnet50,
    fcn_resnet101,
    deeplabv3_resnet50,
    deeplabv3_resnet101,
    deeplabv3_mobilenet_v3_large,
    lraspp_mobilenet_v3_large,
)
from torchvision.models.squeezenet import squeezenet1_0, squeezenet1_1
from torchvision.models.vgg import vgg11, vgg13, vgg16, vgg19, vgg11_bn, vgg13_bn, vgg16_bn, vgg19_bn

#
# failue cases in this script
#

# 1. convxnet contains user-defined nn.Parameters, please refer to test_convnext for more detials
# from torchvision.models.convnext import convnext_tiny, convnext_small, convnext_base, convnext_large

# 2. unknown issues
# from torchvision.models.optical_flow import raft_large

# 3. unknown issues
#from torchvision.models.shufflenetv2 import (
#    shufflenet_v2_x0_5,
#    shufflenet_v2_x1_0,
#    shufflenet_v2_x1_5,
#    shufflenet_v2_x2_0,
#)

# 4. unknown issues
#from torchvision.models.swin_transformer import swin_t, swin_s, swin_b

if __name__=='__main__':

    entries = globals().copy()

    import torch
    import torch.nn as nn
    import torch_pruning as tp
    import random

    def random_prune(model, example_inputs, output_transform):
        from torchvision.models.vision_transformer import VisionTransformer

        model.cpu().eval()
        model = tp.helpers.gconv2convs(model)
        prunable_module_type = ( nn.Conv2d, nn.BatchNorm2d )
        prunable_modules = [ m for m in model.modules() if isinstance(m, prunable_module_type) ]
        ori_size = tp.utils.count_params( model )
        user_defined_parameters = None
        if isinstance(model, VisionTransformer):
            user_defined_parameters = [model.class_token, model.encoder.pos_embedding]
        DG = tp.DependencyGraph().build_dependency( model, example_inputs=example_inputs, output_transform=output_transform, user_defined_parameters=user_defined_parameters )
        for layer_to_prune in prunable_modules:
            # select a layer

            if isinstance( layer_to_prune, nn.Conv2d ):
                prune_fn = tp.prune_conv_out_channel
            elif isinstance(layer_to_prune, nn.BatchNorm2d):
                prune_fn = tp.prune_batchnorm
            elif isinstance(layer_to_prune, nn.Linear):
                prune_fn = tp.prune_linear_out_channel

            ch = tp.utils.count_prunable_channels( layer_to_prune )
            if ch==1: continue
            n_to_prune = min( ch//2, 10 )
            if isinstance(model, VisionTransformer):
                num_heads = model.encoder.layers[0].num_heads
                n_to_prune = n_to_prune % num_heads * num_heads
            rand_idx = random.sample( list(range(ch)), n_to_prune )
            plan = DG.get_pruning_plan( layer_to_prune, prune_fn, rand_idx)
            if DG.check_pruning_plan(plan):
                plan.exec()
        print(model)
        if isinstance(model, VisionTransformer): # Torchvision uses a static hidden_dim for reshape
            model.hidden_dim = model.conv_proj.out_channels
        print(model)

        with torch.no_grad():
            if isinstance(example_inputs, dict):
                out = model( **example_inputs )
            else:
                out = model( example_inputs )
            if output_transform:
                out = output_transform(out)
            print(model_name)
            print( "  Params: %s => %s"%( ori_size, tp.utils.count_params(model) ) )
            if isinstance(out, dict):
                print( "  Output:")
                for o in out.values():
                    print(o.shape)
            else:
                print( "  Output:", out.shape )
            print("------------------------------------------------------\n")

    for model_name, entry in entries.items():
        if not callable(entry):
            continue
        if 'inception' in model_name:
            example_inputs = torch.randn(1,3,299,299)
        elif 'raft' in model_name:
            example_inputs = {'image1': torch.randn(1,3,224,224), 'image2': torch.randn(1,3,224,224)}
        else:
            example_inputs = torch.randn(1,3,224,224)
        
        if 'googlenet' in model_name or 'inception' in model_name:
            model = entry(aux_logits=False)
        elif 'fcn' in model_name or 'deeplabv3' in model_name:
            model = entry(aux_loss=None)
        else:
            model = entry() 
        
        if 'fcn' in model_name or 'deeplabv3' in model_name:
            output_transform = lambda x: x['out']
        else:
            output_transform = None
        print(model_name)
        random_prune(model, example_inputs=example_inputs, output_transform=output_transform)