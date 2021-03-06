import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from matplotlib import cm
import xclim as xc


def xr_collapse_to_global_time_series(da):
    """
    Collapses an array across days of a year and then across space.

    Parameters
    ----------
    da: xr.DataArray
        with 'time', 'lon' and 'lat' dimensions.

    Returns
    -------
    xr.DataArray with only a 'year' dimension.
    """

    collapsed_across_days = xr_average_across_days_of_year(da)
    global_time_series = xr_collapse_across_space(collapsed_across_days)
    return global_time_series


def xr_collapse_across_space(da, weighting="GMST"):

    """
    Collapses an array across weighted longitude and latitude.

    Parameters
    ----------
    da: xr.DataArray
        with 'lon' and 'lat' dimensions.
    weighting: str
        One of ["GMST"].
    Returns
    -------
    data array without 'lon' and 'lat' dimensions.
    """
    if weighting == "GMST":
        lat_weights = np.cos(da["lat"] * np.pi / 180.0)
        ones = xr.DataArray(np.ones(da.shape), dims=da.dims, coords=da.coords)
        weights = ones * lat_weights
        masked_weights = weights.where(~da.isnull(), 0)

        out = (da * masked_weights).sum(dim=("lat", "lon")) / (masked_weights).sum(
            dim=("lat", "lon")
        )
    else:
        raise ValueError(f"{weighting} is an unknown weighting scheme")

    return out


def apply_xr_collapse_across_time(
    da, slices=[("2020", "2040"), ("2040", "2060"), ("2060", "2080"), ("2080", "2100")]
):

    """
    Groups an array by time slices and collapses each slice across time.

    Parameters
    ----------
    da : xr.DataArray
        with 'time' dimension
    slices : list of tuple of str
    Returns
    ------
    dict of data array each key representing the given slice
    """

    results = {}
    for sl in slices:
        results[f"{sl[0]}_{sl[1]}"] = xr_collapse_across_time(da=da, time_slice=sl)
    return results


def xr_collapse_across_time(da, time_slice=("2080", "2100")):
    """
    Slices an array along time and averages across time.

    Parameters
    ----------
    da : xr.DataArray
        with 'time' dimension
    time_slice : tuple of str
        first and last date of sub-period to keep.
    Returns
    ------
    data array with 'time' dropped
    """

    return da.sel(time=slice(time_slice[0], time_slice[1])).mean("time")


def xr_average_across_days_of_year(da):
    """
    Collapses an array across days of each year.

    Parameters
    ----------
    da: xr.DataArray
        with 'time' dimension

    Returns
    -------
    xr.DataArray with a 'year' dimension instead of 'time'
    """

    return da.groupby("time.year").mean()


def xr_count_across_days_of_year(da, count_above=95.0):

    """
    Parameters
    ----------
    da: xr.DataArray
        with 'time' dimensions.
    count_above: float

    Returns
    -------
    data array with a 'year' dimension instead of 'time'.
    """

    da_count = da.where(da > count_above).groupby("time.year").count()
    da_count = da_count.rename(year="time")
    return da_count


def xc_maximum_consecutive_dry_days(da, thresh=0.0005):
    return xc.indicators.atmos.maximum_consecutive_dry_days(
        da, thresh=thresh, freq="YS"
    )


def xc_rx5day(da):
    return xc.indicators.icclim.RX5day(da, freq="YS")

def xr_quantiles_across_time_by_cell(da, q, cells):

    """
    Parameters
    ----------
    da : xr.DataArray
    q : Any
    cells : list of tuples

    Returns
    -------
    list of data arrays
    """

    results = {}
    for c in cells:
        results[c] = da.sel(lat=c[0], lon=c[1], drop=True).quantile(q=q, dim='time')
    return results




def plot_colored_maps(da, common_title, units, color_bar_range):
    """
    Produces a grid of maps colored with the data of a sequence of arrays containing lon and lat dimensions.

    Parameters
    ----------
    da : dict
        keys are str pointing to xr.DataArray objects with lat and lon dimension
    common_title : str
    units : str
    color_bar_range : tuple
    """

    fig, axes = plt.subplots(
        1,
        len(da),
        figsize=(6.4 * 3, 4.8 * 3),
        subplot_kw={"projection": ccrs.PlateCarree()},
    )
    cmap = cm.cividis
    i = 0
    for name, subda in da.items():

        im = subda.plot(
            ax=axes[i],
            cmap=cmap,
            transform=ccrs.PlateCarree(),
            add_colorbar=False,
            vmin=color_bar_range[0],
            vmax=color_bar_range[1],
        )

        axes[i].coastlines()
        axes[i].add_feature(cfeature.BORDERS, linestyle=":")
        axes[i].set_title("{} {}".format(common_title, name))

        i = i + 1

    # Adjust the location of the subplots on the page to make room for the colorbar
    # fig.subplots_adjust(
    #     bottom=0.02, top=0.9, left=0.05, right=0.95, wspace=0.1, hspace=0.01
    # )

    # Add a colorbar axis at the bottom of the graph
    # cbar_ax = fig.add_axes([0.2, 0.2, 0.3, 0.03])

    # Draw the colorbar
    cbar_title = units
    cbar = fig.colorbar(
        im,
        label=cbar_title,
        orientation="horizontal",
        ax=axes.ravel().tolist(),
        fraction=0.046,
        pad=0.04,
    )


def plot_colored_timeseries(da, title, units):

    """
    Produces overlayed colored line graphs from data sequences that have a time dimension.

    Parameters
    ----------
    da : dict
        keys are str pointing to a dict['temporal_data', 'color', 'linestyle']. The former entry is a xr.DataArray object.
    title : str
    units : str
    """

    fig = plt.figure(figsize=(6.4 * 3, 4.8 * 3))
    for name, material in da.items():
        subda = material["temporal_data"]
        subda.plot(label=name, linestyle=material["linestyle"], color=material["color"])
    plt.legend()
    plt.ylabel("{}".format(units))
    plt.title("{}".format(title))
