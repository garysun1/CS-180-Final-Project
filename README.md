# Project Proposal

## Abstract

We are making a video tour of Berkeley landmarks in which anyone crossing a line in the frame steps from the real campus into another season, at night, a century ago, or as a painting. A tripod camera sees the same background in every frame, so we restyle one clean background image, and the new world cannot flicker. We then paste the real passersby back in. The line doubles as a quality test: if the halves are off by even a few pixels, buildings visibly break where they cross it. The final video closes with a short segment showing how each shot was made.

## 1. Background

Restyling a single photo is now routine. Image-to-image translation (pix2pix; CycleGAN's summer-to-winter Yosemite) and diffusion guided by an image's structure (ControlNet) convincingly turn one still into a painting or a snowy scene. However, video is harder. Restyling each frame independently makes textures flicker and buildings wobble. Today's video restyling models (research systems like VISTA and FreeVIS; tools like Runway Aleph 2.0, Luma Modify Video and Wan VACE) regenerate every pixel of every frame. As a result, building geometry drifts and quality degrades on clips longer than a few seconds. A fixed camera sidesteps this.

## 2. Approach

A fixed camera turns a video problem into an image problem: every frame shows the same background, and only the people change. Our pipeline has five steps:

1. **Clean background.** The per-pixel median over the clip erases anyone who keeps moving.
2. **Restyle once.** We edit that one image from a text prompt with FLUX.2 Klein 9B, Qwen-Image-Edit-2511, or SDXL with ControlNet edge guidance, and keep whichever best preserves the buildings.
3. **Re-align.** Editors still nudge geometry. We match features across the two images with a learned matcher and fit a homography, adding a local warp near the line if drift remains.
4. **Cut out people.** SAM 3 tracks every person in the original video from the prompt "person." Shadows the mask misses carry over as the ratio of each frame to the clean background.
5. **Composite.** People appear as filmed on the real side. On the restyled side, we test two options: keep them as filmed, or match them to the style (black-and-white in the past, darker at night), so a person visibly changes the moment they cross the line.

The restyled background is one still image, so it cannot flicker, at full resolution and for any clip length. It costs a few dozen image generations instead of a video model's compute. This is the simplest case of editing a video through one shared image (Layered Neural Atlases; CoDeF). Those methods must learn how each frame maps onto the shared image; with a tripod, that map is the identity.

## 3. Data

Our data is our own tripod footage, and each clip holds two things we separate: the still scene and the people moving through it. We'll shoot 1–3 minute 4K clips of Sather Gate, the Campanile, and one or two more landmarks from fixed spots. Exposure, focus, and white balance stay locked so the camera itself adds no change.

## 4. Evaluation

The seam is our main metric: a misaligned background shows up as building edges that jump where they cross the line. We'll measure that jump by comparing edge maps along the seam before and after alignment, aiming for under 2 pixels. To test the people, we composite them back onto the unedited clean background, where the result should match the original footage exactly.

## 5. Progress and Plan

Our first experiment is Sather Gate. We'll shoot one clip, build the clean background, restyle it with all three editors, and measure seam drift. That picks our model and shows whether one homography is enough. As a stretch, we may split the frame by distance instead of a vertical line: everything near the camera stays real, and everything far away is restyled, so a person walking away from the camera gradually takes on the new style. We would like to settle its scope at the first check-in.
