"""Contexto temporal para las features de cada época."""

import pandas as pd


def add_temporal_context(
    features: pd.DataFrame,
    neighbors: int = 2,
    rolling_windows: tuple[int, ...] = (11,),
    difference_offsets: tuple[int, ...] = (),
    difference_tokens: tuple[str, ...] = (),
) -> pd.DataFrame:
    """Concatena vecinas, medias y cambios temporales sin cruzar registros."""

    if features.empty:
        raise ValueError("No se puede crear contexto para un DataFrame vacío")
    if neighbors < 0:
        raise ValueError("neighbors no puede ser negativo")

    parts = [features.add_suffix("_t0")]
    for offset in range(1, neighbors + 1):
        parts.append(features.shift(offset).add_suffix(f"_t-{offset}"))
        parts.append(features.shift(-offset).add_suffix(f"_t+{offset}"))

    for window in rolling_windows:
        if window <= 0 or window % 2 == 0:
            raise ValueError("Las ventanas móviles deben ser impares y positivas")
        parts.append(
            features.rolling(window, center=True, min_periods=1)
            .mean()
            .add_suffix(f"_movil{window}")
        )

    selected = [
        column
        for column in features.columns
        if any(token in column for token in difference_tokens)
    ]
    for offset in difference_offsets:
        if offset <= 0:
            raise ValueError("Los offsets temporales deben ser enteros positivos")
        if selected:
            current = features[selected]
            previous = current.shift(offset)
            following = current.shift(-offset)
            parts.append(
                current.sub(previous)
                .fillna(0.0)
                .add_suffix(f"_delta_t-{offset}")
            )
            parts.append(
                following.sub(current)
                .fillna(0.0)
                .add_suffix(f"_delta_t+{offset}")
            )

    return pd.concat(parts, axis=1).bfill().ffill()
