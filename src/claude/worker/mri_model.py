import torch
import torch.nn as nn


class ConvBlock(nn.Module):
    """Conv3d x2 + BN + ReLU block"""
    def __init__(self, in_ch, out_ch):
        super().__init__()
        self.block = nn.Sequential(
            nn.Conv3d(in_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm3d(out_ch),
            nn.ReLU(inplace=True),
            nn.Conv3d(out_ch, out_ch, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm3d(out_ch),
            nn.ReLU(inplace=True),
        )

    def forward(self, x):
        return self.block(x)


class ChannelAttention(nn.Module):
    """Squeeze-and-Excitation style channel attention"""
    def __init__(self, channels, reduction=8):
        super().__init__()
        self.fc = nn.Sequential(
            nn.Linear(channels, channels // reduction, bias=False),
            nn.ReLU(inplace=True),
            nn.Linear(channels // reduction, channels, bias=False),
            nn.Sigmoid(),
        )

    def forward(self, x):
        # x: (B, C, D, H, W)
        b, c = x.size(0), x.size(1)
        y = x.view(b, c, -1).mean(dim=2)  # GAP -> (B, C)
        y = self.fc(y).view(b, c, 1, 1, 1)
        return x * y


class ROIAttention(nn.Module):
    """Learnable spatial attention map for ROI weighting"""
    def __init__(self, spatial_size=(96, 112, 96)):
        super().__init__()
        self.weight_map = nn.Parameter(torch.ones(1, 1, *spatial_size))

    def forward(self, x):
        return x * torch.sigmoid(self.weight_map)


class CNNAttention3D(nn.Module):
    """
    3D CNN with ROI Attention for MRI classification.
    Architecture from trained .pth files (cn_f189, ci_f184).
    Input: (B, 1, 96, 112, 96)
    """
    def __init__(self, num_classes=2, spatial_size=(96, 112, 96)):
        super().__init__()

        self.roi_attention = ROIAttention(spatial_size)

        self.block1 = ConvBlock(1, 32)
        self.block2 = ConvBlock(32, 64)
        self.block3 = ConvBlock(64, 128)
        self.block4 = ConvBlock(128, 256)

        self.pool = nn.MaxPool3d(kernel_size=2, stride=2)

        self.attn = ChannelAttention(256, reduction=8)

        self.gap = nn.AdaptiveAvgPool3d(1)

        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(256, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes),
        )

    def forward(self, x):
        # ROI attention on input
        x = self.roi_attention(x)

        x = self.pool(self.block1(x))
        x = self.pool(self.block2(x))
        x = self.pool(self.block3(x))
        x = self.pool(self.block4(x))

        x = self.attn(x)
        x = self.gap(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)

        return x


class CNNEncoder3D(nn.Module):
    """
    Model 184 (MCI vs AD): encoder[0-3] + ROI attention (no SE attention)
    Same conv structure as CNNAttention3D but with ModuleList naming.
    """
    def __init__(self, num_classes=2, spatial_size=(96, 112, 96)):
        super().__init__()
        self.roi_attention = ROIAttention(spatial_size)
        self.encoder = nn.ModuleList([
            ConvBlock(1, 32),
            ConvBlock(32, 64),
            ConvBlock(64, 128),
            ConvBlock(128, 256),
        ])
        self.pool = nn.MaxPool3d(kernel_size=2, stride=2)
        self.gap = nn.AdaptiveAvgPool3d(1)
        self.classifier = nn.Sequential(
            nn.Dropout(0.5),
            nn.Linear(256, 64),
            nn.ReLU(inplace=True),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes),
        )

    def forward(self, x):
        x = self.roi_attention(x)
        for block in self.encoder:
            x = self.pool(block(x))
        x = self.gap(x)
        x = x.view(x.size(0), -1)
        x = self.classifier(x)
        return x


def get_model(model_name="cnn_attention_3d", num_classes=2, device="cpu"):
    """Factory function to get model instance."""
    if model_name == "cnn_encoder_3d":
        model = CNNEncoder3D(num_classes=num_classes)
    else:
        model = CNNAttention3D(num_classes=num_classes)
    return model.to(device)
