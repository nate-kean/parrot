"""
crimsoBOT image processing
https://github.com/crimsobot/crimsoBOT/blob/master/crimsobot/utils/image.py
MIT License
Copyright (c) 2019 crimso, williammck
"""

import logging
from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO
from typing import Concatenate, cast

import aiohttp
from PIL import Image, ImageOps, ImageSequence

from parrot import config
from parrot.utils import executor_function, tag
from parrot.utils.types import AnyUser


type ImageProcessingFunction[**P] = Callable[
	Concatenate[Image.Image, P], Image.Image
]


def gif_frame_transparency(img: Image.Image) -> Image.Image:
	# get alpha mask
	alpha = img.convert("RGBA").split()[-1]
	# convert back to P mode but only using 255 of available 256 colors
	img = img.convert("RGB").convert(
		"P", palette=Image.Palette.ADAPTIVE, colors=255
	)
	# set all pixel values in alpha below threshhold to 255 and the rest to 0
	mask = Image.eval(alpha, lambda a: 255 if a <= 88 else 0)
	# paste the color of index 255 and use alpha as a mask
	img.paste(255, mask)  # the transparency index will later be set to 255
	return img


def image_to_buffer(
	image_list: list[Image.Image],
	durations: tuple[int, ...] | None = None,
	it_loops: bool | None = None,
) -> BytesIO:
	buffer = BytesIO()

	if not durations:
		image_list[0].save(buffer, "WEBP")
	else:
		giffed_frames: list[Image.Image] = []
		for frame in image_list:
			new_frame = gif_frame_transparency(frame)
			giffed_frames.append(new_frame)
		if it_loops:
			giffed_frames[0].save(
				buffer,
				format="GIF",
				transparency=255,
				append_images=giffed_frames[1:],
				save_all=True,
				duration=durations,
				disposal=2,
				loop=0,
			)
		else:
			giffed_frames[0].save(
				buffer,
				format="GIF",
				transparency=255,
				append_images=giffed_frames[1:],
				save_all=True,
				duration=durations,
				disposal=2,
			)
	buffer.seek(0)
	return buffer


async def fetch_image(url: str) -> Image.Image:
	"""Determine type of input, return image file."""
	async with aiohttp.ClientSession() as session:
		async with session.get(url, allow_redirects=False) as response:
			img_bytes = await response.read()
			return Image.open(BytesIO(img_bytes))


# below are the blocking image functions (that support GIF) which require the
# executor_function wrapper
def invert_flip_img(img: Image.Image) -> Image.Image:
	# get image size, resize if too big
	width, height = img.size
	if max(width, height) > 500:
		ratio = max(width, height) / 500
		img = img.resize(
			(int(width / ratio), int(height / ratio)),
			resample=Image.Resampling.BICUBIC,
		)
	img = ImageOps.mirror(img)
	# don't invert alpha channel
	alpha = img.convert("RGBA").split()[-1]
	img = img.convert("RGB")
	img = ImageOps.invert(img)
	img.putalpha(alpha)
	return img


def resize_img(img: Image.Image, scale: float) -> Image.Image:
	width, height = img.size
	return img.resize(
		(int(width * scale), int(height * scale)),
		resample=Image.Resampling.LANCZOS,
	)


@executor_function
def process_lower_level[**P](
	img: Image.Image,
	effect: ImageProcessingFunction[P],
	*args: P.args,
	**kwargs: P.kwargs,
) -> BytesIO:
	# this will only loop once for still images
	frames: list[Image.Image] = []
	durations: list[int] = []

	# if a GIF loops, it will have the attribute loop = 0; if not, then
	# attribute does not exist
	image_loop = getattr(img.info, "loop", False)

	for _ in ImageSequence.Iterator(img):
		if image_loop:
			duration: int = img.info["duration"]
			durations.append(duration)
		img_out = effect(
			cast(Image.Image, img).convert("RGBA"), *args, **kwargs
		)
		frames.append(img_out)

	buffer = image_to_buffer(frames, tuple(durations), image_loop)
	return buffer


@dataclass
class AntiavatarFile:
	buffer: BytesIO
	ext: str


async def create_antiavatar_file(user: AnyUser) -> AntiavatarFile:
	# grab user image and covert to RGBA
	img = await fetch_image(user.display_avatar.url)
	is_gif = getattr(img, "is_animated", False)

	if is_gif:
		n_frames = cast(int, getattr(img, "n_frames"))
		if n_frames > config.image.max_frames:
			raise NotImplementedError(
				"GIF too long; need to process only first frame"
			)
		else:
			logging.info(
				f"Processing GIF avatar for {tag(user)}... ",
				f"{img.width} \u2a09 {img.height} pixels · {n_frames} frames",
			)

	# original image begins processing
	buffer = await process_lower_level(img, invert_flip_img)
	n_bytes = buffer.getbuffer().nbytes

	# if file too large to send via Discord, then resize
	while n_bytes > config.image.max_filesize_bytes:
		# recursively resize image until it meets Discord filesize limit
		img = Image.open(buffer)
		scale = (
			0.9 * config.image.max_filesize_bytes / n_bytes
		)  # 0.9x bias to help ensure it comes in under max size
		buffer = await process_lower_level(img, resize_img, scale)
		n_bytes = buffer.getbuffer().nbytes

	logging.info(f"Generated new antiavatar for {tag(user)}")
	return AntiavatarFile(
		buffer=buffer, ext=img.format if img.format is not None else "png"
	)
