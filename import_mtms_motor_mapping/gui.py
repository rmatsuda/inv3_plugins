import os
import wx
import numpy as np
from pubsub import pub as Publisher
from scipy.io import loadmat


class Window(wx.Dialog):
    def __init__(self, parent):
        super().__init__(
            parent,
            title="Import mTMS targets",
            style=wx.DEFAULT_DIALOG_STYLE | wx.FRAME_FLOAT_ON_PARENT,
        )
        self._init_gui()

    def _init_gui(self):
        wildcard: str = "MATLAB files (*.mat)|*.mat"
        current_dir = os.path.abspath(".")
        dlg_message = "Import mTMS MAT file"
        dlg_style = wx.FD_OPEN | wx.FD_CHANGE_DIR

        dlg = wx.FileDialog(
            None,
            message=dlg_message,
            wildcard=wildcard,
            defaultDir=current_dir,
            style=dlg_style,
        )
        dlg.SetFilterIndex(0)

        try:
            if dlg.ShowModal() == wx.ID_OK:
                filename = dlg.GetPath()

                mat_data = loadmat(filename)

                # find the first struct (skip __header__, __globals__, etc.)
                struct_key = None
                for key in mat_data.keys():
                    if not key.startswith("__"):
                        struct_key = key
                        break

                if struct_key is None:
                    wx.MessageBox("No struct found in MAT file", "InVesalius 3")
                    return

                data_struct = mat_data[struct_key]

                try:
                    x = data_struct["x"][0, 0]
                    y = data_struct["y"][0, 0]
                except Exception:
                    wx.MessageBox("Struct does not contain 'x' and 'y' fields", "InVesalius 3")
                    return

                if x.shape[1] != y.shape[1]:
                    wx.MessageBox(
                        "'x' and 'y' must have the same number of entries",
                        "InVesalius 3"
                    )
                    return

                # Define bins and labels
                bin_edges = [-80, -40, 0, 40, 80]
                bin_labels = ["Bin1", "Bin2", "Bin3", "Bin4"]
                bin_colors = [(1,0,0), (0,1,0), (0,0,1), (1,1,0)]  # optional colors per bin

                # Prepare per-bin brain targets
                for bin_idx in range(len(bin_labels)):
                    bin_targets = []

                    for i in range(x.shape[1]):
                        x_offset = float(x[0, i])
                        y_offset = float(x[1, i])
                        orientation = float(x[2, i])
                        mep_value = float(y[0, i])

                        # Project onto cortical sphere
                        r_sq = x_offset ** 2 + y_offset ** 2
                        sphere_radius_sq = 70 ** 2

                        if r_sq >= sphere_radius_sq:
                            z_val = -85.0
                        else:
                            z_val = -85.0 + np.sqrt(sphere_radius_sq - r_sq)

                        # Determine the bin index for this orientation
                        target_bin_idx = np.digitize(orientation, bin_edges) - 1
                        target_bin_idx = max(0, min(target_bin_idx, len(bin_labels)-1))

                        # Only include target if it belongs to the current bin
                        if target_bin_idx == bin_idx:
                            label = f"{bin_labels[bin_idx]}_{i}"
                            color = bin_colors[bin_idx]

                            bin_targets.append({
                                "position": [y_offset, -x_offset, z_val],
                                "orientation": [0.0, 0.0, -orientation],
                                "color": color,
                                "length": 0.3,
                                "mtms": [x_offset, y_offset, orientation, 0.0],
                                "mep_value": mep_value,
                                "label": label
                            })

                    # Send this bin's targets to InVesalius
                    wx.CallAfter(Publisher.sendMessage, "Duplicate marker", duplicate_brain_target_list=False)
                    wx.CallAfter(Publisher.sendMessage, "Set brain targets", brain_targets=bin_targets)

        except Exception as e:
            wx.MessageBox(f"Invalid MAT file.\nError: {e}", "InVesalius 3")
            self._init_gui()

        self.Destroy()
        dlg.Destroy()


if __name__ == "__main__":
    app = wx.App()
    window = Window(None)
    window.Show()
    app.MainLoop()
