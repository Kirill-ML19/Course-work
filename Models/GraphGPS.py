import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GINEConv
from torch_geometric.nn.norm import LayerNorm
from torch_geometric.utils import get_laplacian, to_dense_adj
import numpy as np
import scipy.sparse as sp
from scipy.sparse.linalg import eigsh


class LaplacianPE(nn.Module):
    def __init__(self, k=10):
        super().__init__()
        self.k = k
        self.linear = nn.Linear(k, k)
        
    def forward(self, x, edge_index):
        try:
            num_nodes = x.shape[0]
            
            edge_index, edge_weight = get_laplacian(
                edge_index, num_nodes=num_nodes, normalization='sym'
            )
            
            row, col = edge_index.numpy()
            laplacian = sp.coo_matrix(
                (edge_weight.numpy(), (row, col)),
                shape=(num_nodes, num_nodes)
            )
            
            eigenvalues, eigenvectors = eigsh(laplacian, k=self.k+1, which='SM')
            
            pe = torch.tensor(eigenvectors[:, 1:self.k+1], dtype=torch.float32)
            
            pe = self.linear(pe)
            
            return pe.to(x.device)
            
        except Exception as e:
            return torch.randn(x.shape[0], self.k).to(x.device)


class GPSLayer(nn.Module):
    def __init__(self, dim, edge_dim, heads=4, dropout=0.1, local_dropout=0.1):
        super().__init__()
        
        self.dim = dim
        self.heads = heads
        
        self.local_mlp = nn.Sequential(
            nn.Linear(dim, dim),
            nn.ELU(),
            nn.Linear(dim, dim)
        )
        self.local_conv = GINEConv(
            nn=self.local_mlp,
            edge_dim=edge_dim,
            train_eps=True
        )
        self.local_norm = LayerNorm(dim)
        self.local_dropout = nn.Dropout(local_dropout)
        
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
        
    def forward(self, x, edge_index, edge_attr=None, batch=None):
        num_nodes = x.shape[0]
        
        x_local = self.local_conv(x, edge_index, edge_attr=edge_attr)
        x_local = self.local_norm(x_local)
        x_local = F.elu(x_local)
        x_local = self.local_dropout(x_local)
        
        x = x + x_local
        
        x_global = x.unsqueeze(0)  
        
        attn_out, _ = self.attn(x_global, x_global, x_global)
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
        edge_dim,
        hidden_dim=64,
        embed_dim=64,
        num_targets=5,
        num_layers=3,
        pe_dim=10,
        heads=4,
        dropout=0.3
    ):
        super().__init__()
        
        self.pe_encoder = LaplacianPE(k=pe_dim)
        
        self.input_proj = nn.Sequential(
            nn.Linear(node_dim + pe_dim, hidden_dim),
            nn.ELU(),
            nn.Dropout(dropout)
        )
        
        self.layers = nn.ModuleList([
            GPSLayer(
                dim=hidden_dim,
                edge_dim=edge_dim,
                heads=heads,
                dropout=dropout
            )
            for _ in range(num_layers)
        ])
        
        self.head = nn.Sequential(
            nn.Linear(hidden_dim, embed_dim),
            nn.ELU(),
            nn.Dropout(dropout),
            nn.Linear(embed_dim, embed_dim // 2),
            nn.ELU(),
            nn.Dropout(dropout),
            nn.Linear(embed_dim // 2, num_targets)
        )
        
    def add_noise(self, x, noise_std=0.02):

        if self.training:
            return x + torch.randn_like(x) * noise_std

        return x

    def forward(self, x, edge_index, edge_attr=None, batch=None):
        pe = self.pe_encoder(x, edge_index)  
        
        x = torch.cat([x, pe], dim=1)  
    
        x = self.input_proj(x) 

        x= self.add_noise(x, noise_std=0.06)
        
        for layer in self.layers:
            x = layer(x, edge_index, edge_attr=edge_attr, batch=batch)
        
        out = self.head(x)  
        
        return out