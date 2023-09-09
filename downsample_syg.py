import numpy as np
import syglass
from syglass import pyglass
from tabulate import tabulate

import sys
import warnings

warnings.simplefilter(action='ignore', category=FutureWarning)


bytes_suffixes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
def pretty_data_size(nbytes):
    i = 0
    while nbytes >= 1024 and i < len(bytes_suffixes)-1:
        nbytes /= 1024.
        i += 1
    f = ('%.2f' % nbytes).rstrip('0').rstrip('.')
    return '%s %s' % (f, bytes_suffixes[i])


def downsample_project(project_path : str):
	if not syglass.is_project(project_path):
		print("The file at the path provided is not a valid syGlass project.")
		return
	
	project = syglass.get_project(project_path)
	block_size = project.get_block_size()
	resolution_map = project.get_resolution_map()
	resolution_count = len(resolution_map)
	data_type = project.get_data_type()
	channel_count = project.get_channel_count()

	if resolution_count == 1:
		print("The specified project only contains one resolution level; nothing to downsample.")
		return
	
	bytes_per_voxel = 1
	if data_type == syglass.ProjectDataType.UINT8:
		bytes_per_voxel = channel_count
	elif data_type == syglass.ProjectDataType.UINT16 or data_type == syglass.ProjectDataType.HALF_FLOAT:
		bytes_per_voxel = channel_count * 2
	else:
		bytes_per_voxel = channel_count * 4

	resolution_options = []
	for i in range(1, resolution_count):
		block_count = resolution_map[i]
		blocks_per_dimension = block_count ** (1.0 / 3.0)
		resolution = (block_size * blocks_per_dimension).astype(np.uint64)
		data_size = resolution[0] * resolution[1] * resolution[2] * bytes_per_voxel
		resolution_options.append([i, resolution, pretty_data_size(data_size)])

	print("\n" + tabulate(resolution_options, headers=["Option", "Resolution", "Data Size"], tablefmt="simple_grid"))

	resolution_selected = False
	while not resolution_selected:

		index = int(input("\nEnter an downsampling option number from the table above: "))
		if index < 1 or index >= resolution_count:
			print("\nThe entered number is not an option from the table. Please try again.")
		else:
			resolution_selected = True


if __name__ == "__main__":
	if len(sys.argv) != 2:
		print("Usage: python downsample_syg.py [path/to/syGlass/file.syg]")
	else:
		downsample_project(sys.argv[1])


