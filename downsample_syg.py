from collections import namedtuple
from glob import glob
import numpy as np
from pathlib import Path
import syglass
from syglass import pyglass
from tabulate import tabulate
from tqdm import tqdm
import tifffile

import os
import sys
import shutil
import time
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


def create_project(project_name : str):
	project = pyglass.CreateProject(pyglass.path("."), project_name)

	directory_description = pyglass.DirectoryDescription()
	reference_file = glob(os.path.join("temp/*.tiff"))[0].replace("\\", "/")
	directory_description.InspectByReferenceFile(reference_file)

	data_provider = pyglass.OpenTIFFs(directory_description.GetFileList(), timeSeries=False)
	conversion_driver = pyglass.ConversionDriver()
	conversion_driver.SetInput(data_provider)
	conversion_driver.SetOutput(project)

	print("\nCreating syGlass project...\n")

	conversion_driver.StartAsynchronous()
	with tqdm(total=100) as progress_bar:
		while conversion_driver.GetPercentage() < 100:
				time.sleep(0.25)
				progress_bar.update(conversion_driver.GetPercentage())


def downsample_project(project_path : str):
	if not syglass.is_project(project_path):
		print("\nThe file at the path provided is not a valid syGlass project.")
		return
	
	project = syglass.get_project(project_path)
	block_size = project.get_block_size()
	resolution_map = project.get_resolution_map()
	resolution_count = len(resolution_map)
	data_type = project.get_data_type()
	channel_count = project.get_channel_count()
	timepoint_count = project.get_timepoint_count()

	if resolution_count == 1:
		print("\nThe specified project only contains one resolution level; nothing to downsample.")
		return
	
	if timepoint_count > 1:
		print("\nWarning: timeseries projects are not well-supported by this tool.")
	
	bytes_per_voxel = 1
	if data_type == syglass.ProjectDataType.UINT8:
		bytes_per_voxel = channel_count
	elif data_type == syglass.ProjectDataType.UINT16 or data_type == syglass.ProjectDataType.HALF_FLOAT:
		bytes_per_voxel = channel_count * 2
	else:
		bytes_per_voxel = channel_count * 4

	resolution_options = []
	for i in range(0, resolution_count):
		block_count = resolution_map[i]
		blocks_per_dimension = block_count ** (1.0 / 3.0)
		resolution = (block_size * blocks_per_dimension).astype(np.uint64)
		xyz_resolution = [resolution[2], resolution[1], resolution[0]]
		data_size = resolution[0] * resolution[1] * resolution[2] * bytes_per_voxel
		if i == resolution_count - 1:
			resolution_options.append(["Current", xyz_resolution, pretty_data_size(data_size)])
		else:
			resolution_options.append([i + 1, xyz_resolution, pretty_data_size(data_size)])

	print("\n" + tabulate(resolution_options, headers=["Option", "Resolution", "Data Size"], tablefmt="simple_grid"))

	resolution_selected = False
	resolution_index = 0
	while not resolution_selected:
		resolution_index = int(input("\nEnter an downsampling option number from the table above: "))
		if resolution_index < 1 or resolution_index >= resolution_count:
			print("\nThe entered number is not an option from the table. Please try again.")
		else:
			resolution_selected = True

	image_resolution = resolution_options[resolution_index - 1][1]
	image_resolution.reverse()
	slice_resolution = [1, image_resolution[1], image_resolution[2]]
	slice_offset = np.asarray([0,0,0])

	if os.path.exists("temp"):
		shutil.rmtree("temp")
	os.mkdir("temp")

	print("\nWriting downsampled TIFF files...\n")

	for z in tqdm(range(image_resolution[0])):
		slice_prefix = str(z).zfill(8)
		slice_offset[0] = z
		slice = project.get_custom_block(0, resolution_index - 1, slice_offset, slice_resolution)
		tifffile.imwrite("temp/" + slice_prefix + "_temp.tiff", slice.data)

	new_project_name = Path(project_path).stem + "_Downsampled"
	create_project(new_project_name)
	shutil.rmtree("temp")
	print(f"\nDownsampled project file created in the directory \"{new_project_name}\".")


if __name__ == "__main__":
	if len(sys.argv) != 2:
		print("\nUsage: python downsample_syg.py [path/to/syGlass/file.syg]")
	else:
		downsample_project(sys.argv[1])
