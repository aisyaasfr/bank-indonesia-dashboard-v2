from __future__ import annotations


def apply_plotly_theme(fig, dark: bool = False):
    paper = "#1F2937" if dark else "#FFFFFF"
    plot = "#1F2937" if dark else "#FFFFFF"
    font = "#F3F4F6" if dark else "#172B4D"
    grid = "#374151" if dark else "#E9EDF2"
    fig.update_layout(
        template="plotly_dark" if dark else "plotly_white",
        paper_bgcolor=paper,
        plot_bgcolor=plot,
        font={"family": "Poppins, Arial, sans-serif", "color": font, "size": 12},
        margin={"l": 18, "r": 18, "t": 45, "b": 18},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "right", "x": 1},
        xaxis={"gridcolor": grid, "zerolinecolor": grid},
        yaxis={"gridcolor": grid, "zerolinecolor": grid},
    )
    return fig
