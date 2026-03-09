import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GINConv
from torch_geometric.nn.norm import LayerNorm
from torch_geometric.utils import dropout_edge


class GPSLayer(nn.Module):
    def __init__(self, dim, heads=2, dropout=0.5):
        super().__init__()

        self.local_mlp = nn.Sequential(
            nn.Linear(dim, dim),
            nn.ELU(),
            nn.Linear(dim, dim)
        )

        self.local_conv = GINConv(
            nn=self.local_mlp,
            train_eps=True
        )

        self.local_norm = LayerNorm(dim)
        self.local_dropout = nn.Dropout(dropout)

        self.attn = nn.MultiheadAttention(
            embed_dim=dim,
            num_heads=heads,
            dropout=dropout,
            batch_first=True
        )

        self.attn_norm = LayerNorm(dim)
        self.attn_dropout = nn.Dropout(dropout)

        self.ffn = nn.Sequential(
            nn.Linear(dim, dim * 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(dim * 2, dim)
        )

        self.ffn_norm = LayerNorm(dim)
        self.ffn_dropout = nn.Dropout(dropout)

    def forward(self, x, edge_index):

        residual = x

        x_local = self.local_conv(x, edge_index)
        x_local = self.local_norm(x_local)
        x_local = F.elu(x_local)
        x_local = self.local_dropout(x_local)

        x = residual + x_local

        x_global = x.unsqueeze(0)

        attn_out, _ = self.attn(
            x_global,
            x_global,
            x_global,
            need_weights=False
        )

        attn_out = attn_out.squeeze(0)
        attn_out = self.attn_norm(attn_out)
        attn_out = self.attn_dropout(attn_out)

        x = x + attn_out

        x_ffn = self.ffn(x)
        x_ffn = self.ffn_norm(x_ffn)
        x_ffn = self.ffn_dropout(x_ffn)

        x = x + x_ffn

        return x


class GraphGPSRegressor(nn.Module):
    def __init__(
        self,
        node_dim,
        hidden_dim=32,
        embed_dim=32,
        num_targets=5,
        num_layers=2,
        pe_dim=4,
        heads=2,
        dropout=0.5,
        dropedge_p = 0.2
    ):
        super().__init__()

        self.pe_dim = pe_dim
        self.dropedge_p = dropedge_p

        self.input_proj = nn.Sequential(
            nn.Linear(node_dim + pe_dim, hidden_dim),
            nn.ELU(),
            nn.Dropout(dropout)
        )

        self.layers = nn.ModuleList([
            GPSLayer(
                dim=hidden_dim,
                heads=heads,
                dropout=dropout
            )
            for _ in range(num_layers)
        ])

        self.head = nn.Sequential(
            nn.Linear(hidden_dim, embed_dim),
            nn.ELU(),
            nn.Dropout(dropout),
            nn.Linear(embed_dim, num_targets)
        )

    def add_noise(self, x, noise_std=0.02):
        if self.training:
            return x + torch.randn_like(x) * noise_std
        return x

    def forward(self, x, edge_index):

        x = self.input_proj(x)

        x = self.add_noise(x, noise_std=0.02)

        if self.training and self.dropedge_p > 0:
            edge_index, _ = dropout_edge(edge_index=edge_index, p=self.dropedge_p)

        for layer in self.layers:
            x = layer(x, edge_index)

        out = self.head(x)

        return out