# Cross the Line prior work positioning

> **Superseded (27 November 2026).** The current pitch, the closest work and what we added are in
> [docs/state-of-the-art.md](../../state-of-the-art.md). This page is the 24 November version: its pitch
> line and its flicker claims are out of date.

## The line

> **Today's AI video redraws every frame. A tripod lets us redraw the world once, so reality and its AI twin share one frame, and you can walk across the line between them.**

## The 5-minute pitch

**0:00 · Hook** *(demo: a walker crosses into winter)*

This is a real video of a plaza. On the left, everything is exactly what the camera saw. On the right, it's winter. Watch her walk across the line and into the snow. Today's AI video redraws every frame. A tripod lets us redraw the world once, so reality and its AI twin share one frame, and you can walk across the line between them.

**0:30 · How it's done today**

If you want to turn a video into winter today, there are two kinds of tools.

Video AI (Runway, Luma, the research editors) redraws every pixel of every frame. That is expensive, clips are capped at five to thirty seconds, and because each frame is drawn fresh, buildings shimmer and faces change. Live versions exist, such as StreamDiffusion and Decart, but they need one to four datacenter GPUs, and they redraw you too.

The other kind is the meeting app. Teams, Zoom and Meet generate a background once and paste you on top. That is stable, but it replaces your room. Nobody stands in the real room and the AI room at the same time.

**1:30 · Our trick**

Our trick is a tripod. If the camera never moves, every frame shares one background. We take the per-pixel median over the clip, so anyone who keeps walking disappears and the empty scene remains as one image.

We redraw that one image with Stable Diffusion, using ControlNet so the buildings stay put. It takes a minute or two on a laptop CPU, once per world. Then we cut the people out of the original video and put them back.

Research systems that edit video through one shared image have to learn how every frame maps onto it. With a tripod, that map is the identity, and the shared image is just the median. The world is one picture, so it can't flicker, and the real side is the camera's own pixels.

**2:45 · What it unlocks**

Because both versions line up pixel for pixel, a rule can pick real or AI for every pixel:
- a line you walk across;
- a distance, where everything farther than here becomes a painting. Each person takes the depth of the ground at their feet, so they change as one piece;
- a portal on the ground.

Instead of a hard cut, the world can grow in through the model's own unfinished drawings, the in-between images it makes when you ask for a lighter edit.

The seam checks itself. If the AI moved a building, it shows as a step at the line, and after registration that step is under 0.6 pixels.

Because compositing is cheap, it runs live: a laptop kiosk captures the empty room, draws its twin in seconds, and you walk between them.

**3:45 · What we built on, and what's ours**

We built on Stable Diffusion, ControlNet, SDEdit and Depth Anything, plus tools from this course: median backgrounds, homographies and two-band blending.

Ours:
- the crossing rules;
- placing each person at the depth of their feet;
- the morph through the model's own drawings;
- the seam as an alignment check;
- the live kiosk.

We looked for this crossing in papers, products, filters and art, and didn't find it. The nearest are photographers who blend day and night by hand over months, and AR portals into made-up rooms.

**4:30 · Limits and close**

It needs a still camera, and moving water or trees break the empty scene. Next we film Sather Gate and measure how much a per-frame AI baseline flickers next to ours. But the idea fits in one sentence: draw the world once, then let people walk into it.

## Closest work and how we differ

| Approach | Examples | How we differ |
|---|---|---|
| Video AI redraws every frame | Runway Aleph 2.0, Luma Ray3.2, Wan VACE, TokenFlow | We redraw one image; any length; no flicker in the world |
| Live AI video | StreamDiffusion, Decart MirageLSD, Krea Realtime | They need datacenter GPUs and redraw the person; we keep real pixels and run on a laptop |
| Layered video editing | Neural Atlases, CoDeF, Omnimatte | They learn the shared image per video; a tripod makes it the median |
| AI backgrounds | Teams "Decorate", Zoom, Meet | Generated once, but it replaces the room; ours is the same room, and you cross into it |

## Say / don't say
- Say **"we did not find"**, never "first" or "novel".
- Say **"generate once, composite live"**, never "real-time AI".
- Say **"the world can't flicker"**; masks still can, so don't say "flicker-free video".
- Say **"colour-matched to the world"**, never "relit".
- Say **"registration brings the seam under 0.6 px"**, not "the AI keeps geometry".

*Citations, verdicts and evidence are in `research_notes/Cross the Line prior work positioning/` (full_report.md plus three notes files).*
