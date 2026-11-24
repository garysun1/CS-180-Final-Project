# Precedents and Inspiration for "Cross the Line" (step into another world / another time)

Scope note: research done 2026-11-19 by web search. Three hosts could not be fetched from this session (cal-cs180.github.io, cartoonbrew.com, fxphd.com are outside the session's allowed network), so claims about them come from search-result summaries only and are marked as such. "Borrow" ideas are in the Inferences subsections and are scoped to a 2–3 week student build on top of the existing pipeline (median clean plate → one restyled plate → homography → SAM person masks → composite).

## 1. Interactive art installations: portals, windows and mirrors (including AI-era live restyling, 2023–2026)

### Takeaway
The most memorable installations reduce the idea to one physical frame plus one rule that the visitor's own body triggers. Examples: a round concrete door showing another city live (The Portal), rain that stops where you stand (Rain Room), letters that land on your silhouette (Text Rain), a mirror made of objects (Rozin). AI-era "magic mirrors" (2024–2025) restyle visitors live with per-frame diffusion at low resolution. Our fixed-plate method can do the same at full resolution with no flicker, because only the person mask changes per frame. That difference is a strong pitch for a live demo.

### Cited Findings
**The Portal (Benediktas Gylys, Vilnius–Lublin, 2021–)**
- Two identical circular concrete "doors", each with a large screen and cameras, were installed in Vilnius (near the train station) and Lublin (central square) on 26 May 2021. Each shows whoever is standing at the other unit, live over the Internet. The project came from the Benediktas Gylys Foundation with Vilnius Gediminas Technical University (VILNIUS TECH) — [Wikipedia: Portal (sculptures)](https://www.wikipedia.org/wiki/Portal_(sculptures)); [Go Vilnius](https://www.govilnius.lt/vilnius-invites-residents-to-connect-through-a-portal); [VILNIUS TECH news](https://vilniustech.lt/en/university/news/portal-an-interactive-bridge-to-unity-connects-two-countries-328416/)
- Gylys framed it as an answer to division ("tribalism, a lack of empathy and a narrow perception of the world"). Press widely described it as a "time–space portal" between cities 376 miles apart — [My Modern Met](https://mymodernmet.com/portals-connection-vilnius-lublin); [The Mayor.eu](https://www.themayor.eu:443/en/a/view/time-space-portal-links-vilnius-and-lublin-8064)
- The network grew. New York City–Dublin portals opened 8 May 2024, a later report lists connections to Lublin, Dublin and Philadelphia, and the Vilnius unit moved to the Old Town opposite the Town Hall in April 2025 — [Wikipedia: Portal (sculptures)](https://www.wikipedia.org/wiki/Portal_(sculptures)); [Newstalk (Dublin–Lublin)](https://newstalk.com/news/from-dublin-to-lublin-council-announces-two-new-portal-connections-1758722); [Go Vilnius: Vilnius Portal](https://www.govilnius.lt/vilnius-portal)

**Body-triggered rules: Rain Room, Text Rain, Rozin, Lozano-Hemmer**
- *Rain Room* (Random International, Barbican Curve, London, 2012) is a 100 m² field of falling water. 3D tracking cameras in the ceiling switch off the nozzles in a roughly six-foot radius around each visitor, so people walk through rain without getting wet. LACMA (2019) described it as "the sensory illusion of being able to control the rain." Permanent versions exist, for example in Sharjah, and the concept has been widely copied — [My Modern Met](https://mymodernmet.com/random-international-rain-room); [Hyundai Artlab](https://artlab.hyundai.com/project/random-international-rain-room); [Wikiwand: Random International](https://www.wikiwand.com/en/articles/Random_International)
- *Text Rain* (Camille Utterback and Romy Achituv, 1999). Visitors see a mirrored black-and-white video of themselves with colored letters falling over it. The letters "land" on anything darker than a set threshold and fall again when the obstacle moves. The text is from Evan Zimroth's poem "Talk, You" — [camilleutterback.com: Text Rain](https://camilleutterback.com/projects/text-rain/); [SIGGRAPH history archive](https://history.siggraph.org/?p=15580)
- Daniel Rozin has built mechanical "mirrors" since *Wooden Mirror* (1999). A camera drives motors that move hundreds of physical elements; *Angles Mirror* uses 465 plastic spokes. Rozin: "the contents of the piece is you" — [Dezeen, 21 Feb 2014](https://www.dezeen.com/2014/02/21/mechanical-mirrors-by-daniel-rozin-replicate-images-using-everyday-objects/)
- Rafael Lozano-Hemmer's *Redundant Assembly* (2015) tracks several visitors' faces in real time and superimposes them into one composite portrait. The same paper notes that Rozin's mirrors mainly translate the viewer's image into motion, with no further behavior — [Mirror Ritual paper, arXiv 2004.09685](https://arxiv.org/pdf/2004.09685)

**AI-era "magic mirrors" that restyle visitors live**
- *STOCHASTIC MAN* (Weber Wong, May 2024) is a "real-time AI mirror" sculpture of three stacked vintage CRT TVs. Each shows a live reflection of the viewer in a different painting style — [stochastic-man.cargo.site](https://stochastic-man.cargo.site); [weberwong.cargo.site](https://weberwong.cargo.site/stochastic-man)
- *A-Eye* (2024) premiered at an M+ party during Art Basel. Live pose/motion capture drives a real-time diffusion model, described as "a mirror that doesn't quite mirror". The source is a self-reported portfolio page — [portfolio: A-Eye](https://portfolio-3e6.pages.dev/projects/a-eye)
- *Mirror 3* (Kyle Rudick, Burning Man 2025) transforms participants with AI diffusion models in real time — [Burning Man gallery](https://gallery.burningman.org/asset/a24b9542-106f-4c3e-8cf8-00dc79734b66?i=1174&q=1). Other examples: *Neuron Mirror* (truetrue.studio, 2025) — [Vimeo](https://vimeo.com/1062000602); a Maker Faire "AI Mirror" that reflects people in Ghibli/anime/cultural styles — [Maker Faire](https://makerfaire.com/maker/entry/ai-mirror-78082/); an earlier non-diffusion precedent, Ultravioletto's *Neural Mirror* (2019) — [Dezeen](https://www.dezeen.com/2019/07/12/ultravioletto-neural-mirror-ai-reflection-design/)
- Standard toolchain for these mirrors: StreamDiffusion driven from TouchDesigner. The TouchDiffusion component reports 55–60 FPS with sd-turbo at 512×512 on an RTX 4090, 47 FPS on a 4080 and 37 FPS on a 3090 Ti. A Derivative tutorial builds an interactive "magic mirror" in which webcam motion is turned into AI visuals in real time — [GitHub: olegchomp/TouchDiffusion](https://github.com/olegchomp/TouchDiffusion); [Derivative: Magic Mirror with StreamDiffusion](https://derivative.ca/community-post/tutorial/magic-mirror-effect-working-streamdiffusion-touchdesigner/71161); [Interactive & Immersive HQ](https://interactiveimmersive.io/blog/artificial-intelligence/using-streamdiffusion-with-touchdesigner/)
- At SIGGRAPH Real-Time Live 2025, Sterling showed StreamDiffusion via TouchDesigner in an interactive feedback loop driving laser installations — [SIGGRAPH history: Drawing with Light](https://history.siggraph.org/experience/drawing-with-light-ai-driven-visual-synthesis-for-real-time-laser-installations-by-sterling)

### Inferences
- **Live "Portal" kiosk (top recommendation, about 1 week).** A webcam on a fixed mount, a clean plate grabbed at startup (median of N frames), 4–6 restyled plates generated once, and a fast person segmenter. MediaPipe/YOLO-seg would be needed for real time, because SAM 3 is likely too slow for live use; this is an inference to verify. Compositing then runs at full resolution on a laptop with no per-frame diffusion. The pitch: "unlike STOCHASTIC MAN or TouchDiffusion (512 px, per-frame diffusion, flicker), our world is pixel-stable because we restyle once." A physical cardboard ring or tape line on the floor in front of the camera borrows The Portal's "door" framing and Rain Room's "your body triggers the rule".
- **Borrow Text Rain's threshold rule for the depth mode.** "Anything nearer than depth d stays real" is a direct cousin of "letters land on anything darker than threshold t". Showing the depth map as a live inset makes the rule readable to visitors.
- **Borrow Rozin's "the content is you".** Let the restyled world stay static and stylize only the visitor as they cross, so the visitor becomes the artwork.
- **Borrow Lozano-Hemmer's multi-visitor composite.** In the tripod footage, give each passer-by a different world or era, so the crowd becomes a multiverse.
- **Portal-to-the-past framing.** Show the Sather Gate camera feed side by side with a "1920s Sather Gate" plate, as a portal between two times rather than two cities.

### Gaps
- Could not confirm teamLab, Refik Anadol or Zach Lieberman pieces that specifically use a body-triggered "world swap"; the searches returned nothing usable on them.
- Could not verify press reports (background knowledge only) that the NYC–Dublin portal was temporarily shut in May 2024 after misuse. That would matter only as a "people will clown for the camera" design lesson.
- No reliable numbers on visitor dwell time or engagement for any of these installations.

## 2. Time travel / then-and-now: rephotography, historical overlays, campus history

### Takeaway
"Then and now" works best when the old and new images line up exactly and the viewer controls the transition (swipe or slider). Real archive photos of Sather Gate and the Campanile exist (Bancroft, OAC/Calisphere, Berkeley Historical Society, Berkeley Lab's Then & Now). A "real 1910s" world, aligned to our tripod plate with the same homography step we already have, would be a strong complement to the AI-imagined "1920s" world. Bae–Agarwala–Durand (2010) is the canonical CS citation for matching a historic viewpoint.

### Cited Findings
- **Computational Rephotography** (Soonmin Bae, Aseem Agarwala, Frédo Durand, ACM TOG 29(3), Article 24, June 2010; MIT CSAIL TR-2010-016, April 2010). The authors built a real-time camera-pose estimation and visualization tool that guides the photographer to a historic photo's viewpoint across six degrees of freedom, including the zoom-versus-dolly ambiguity. Pilot studies found that untrained users could not reproduce a reference viewpoint even with simple visualizations. The system was evaluated by rephotographing historical images — [paper PDF](https://people.csail.mit.edu/soonmin/rephoto/rephoto.pdf); [MIT DSpace](https://dspace.mit.edu/handle/1721.1/53705); [dblp](https://dblp.org/rec/journals/tog/BaeAD10)
- **Google Street View "time travel".** Launched April 2014 on desktop Google Maps, it exposes historical Street View imagery back to 2007 through a timeline slider. It was later extended to mobile and Google Earth — [Google blog](https://blog.google/products/maps/go-back-in-time-with-street-view/); [Computerworld](https://www.computerworld.com/article/1518446/go-time-traveling-with-google-maps.html); [Google developer docs](https://developers.google.com/maps/documentation/earth/historical-street-view)
- **Historypin** (launched 2010) is a user-generated archive that overlays historical photos onto Google Street View for comparison. Its smartphone apps were discontinued by 2015 — [PetaPixel, 4 Jun 2010](https://www.petapixel.com/2010/06/04/historypin-places-historical-photographs-over-google-street-view); [Wikipedia: Historypin](https://en.wikipedia.org/wiki/Historypin)
- **WhatWasThere** offered geolocated historical photos with a Street View mode where you "swipe the photo back and forth" between the current view and the old photo. A reviewer noted that alignment was "a bit hit and miss" — [Geography Realm](https://www.geographyrealm.com/whatwasthere-augmented-reality/); [6sqft](https://www.6sqft.com/website-whatwasthere-lets-users-tour-their-neighborhoods-through-historic-photos/)
- **Berkeley Lab "Then & Now"** overlays historic and modern photos taken from the same vantage points, including a UC Berkeley Campanile view from 1943 paired with 2018 — [history.lbl.gov/then-and-now](https://history.lbl.gov/then-and-now/)
- **Bancroft Library "Then and Now: Student Photographs of the Berkeley Campus"** (2003 exhibit) drew on University Archives and Bancroft pictorial collections — [UC Berkeley News archive, 2003](https://newsarchive.berkeley.edu/news/media/releases/2003/03/07_thennow.shtml)
- **Archival Sather Gate images**
  - The Online Archive of California finding aid lists a 1915 Sather Gate view with the Campanile top — [OAC finding aid](https://oac.cdlib.org/findaid/ark:/13030/kt429003bb/dsc/)
  - The Berkeley Historical Society & Museum has c.1909–1910 Sather Gate photographs, including a view through the gate south toward Telegraph — [CatalogIt hub item](https://hub.catalogit.app/berkeley-historical-society-museum/folder/entry/university-of-california-28)
  - Calisphere holds Sather Gate items — [Calisphere](https://calisphere.org/item/55cfbcd616275b1814867806aecbf1e4/)
  - Sources disagree on the gate's completion date (1910 vs 1913), so verify before printing a date on screen — [Calisphere item](https://calisphere.org/item/5284aa6e7f33a9fc3bd43f3f2327240c)
- **Cinemagraphs** (Jamie Beck and Kevin Burg, early 2011, coined March 2011 for New York Fashion Week coverage) are still photos with one looped moving element. Burg said they animated only a small part of each image, partly to stay under Tumblr's file-size limit — [Wikipedia: Cinemagraph](https://en.wikipedia.org/wiki/Cinemagraph); [cinemagraphs.com](https://cinemagraphs.com/what-is-a-cinemagraph); [Flipboard interview](https://about.flipboard.com/inside-flipboard/on-the-red-couch-with-cinemagraph-co-founder-kevin-burg/)

### Inferences
- **"Real archive world".** Pull a public-domain c.1910–1915 Sather Gate photo, shoot our tripod plate from as close to that vantage as possible (a mini Bae et al. moment: put a translucent onion-skin overlay of the archive photo on the camera monitor while framing), then homography-align it. Crossing the line then takes you into the *actual* past. Pair it with the AI "1920s" plate and ask the audience which one is real.
- **AI-restyle the archive photo itself.** Colorize or upscale it, or use the image editor with the archive photo as the target style. This shows the editor drifting away from the real historical geometry, and our seam metric can quantify that.
- **Interactive web slider (WhatWasThere/Street View style).** On the project website, a draggable line over a still frame: left = 2026 real, right = chosen world, with a dropdown for the year or style. Building it is trivial (two stacked images plus CSS clip-path), and it makes the seam-quality story self-evident. WhatWasThere's "hit and miss" alignment is a good foil for our under-2-px seam goal.
- **Cinemagraph shot.** Freeze the restyled world and one person (a "still photo from 1915") while a single real passer-by keeps walking. This is cheap with our masks and reads instantly as time travel.

### Gaps
- No dedicated UC Berkeley rephotography or AR "campus history" app was found. Berkeley Lab's page is the closest.
- Licensing and public-domain status of specific Bancroft/OAC Sather Gate images was not checked. Pre-1929 publication is likely public domain in the US, but each item needs checking.
- Did not find a 2023–2026 "old-photo AR" app with documented reach. Any modern equivalents are unconfirmed.

## 3. Film and animation technique precedents (Spider-Verse glitch, Take On Me, EEAAO, Corridor, per-beat style switching, split screens)

### Takeaway
The Spider-Verse look comes from a small set of print-inspired, rule-based tricks that a student can rebuild in NumPy:
- chromatic aberration / misregistration (offset color channels)
- halftone dots for highlights and hatching for shadows
- switching between animating "on ones" and "on twos"
- design-driven (not simulated) glitch fractures applied to characters *and* buildings when a dimension intrudes

The sequel's rule that each universe gets its own art style and rendering rules maps directly onto our "each world restyles people differently" option. Take On Me, the 500 Days of Summer split screen and Paul Trillo's Sora video each offer one transition idea we can borrow.

### Cited Findings
**Into / Across the Spider-Verse (Sony Pictures Imageworks, 2018 / 2023)**
- Chromatic aberration (red/blue fringes) mimics misregistration on old comic printing presses. It was used with halftoning for highlights and hatching for shadows. Effects were built largely in Houdini, with Nuke and Katana also in the pipeline. These points come from search-result summaries of fxphd/fxguide/SideFX/Foundry coverage; full articles could not be fetched here — [fxphd: Spider-Verse at SIGGRAPH](https://www.fxphd.com/fxblog/spider-verse-at-siggraph/); [SideFX community post](https://www.sidefx.com/community/spider-man-into-the-spider-verse/); [Foundry: graphic look in comp](https://www.foundry.com/insights/film-tv/graphic-look-in-comp-spiderman)
- The "glitch" hits characters, buildings and cars during dimensional disturbances as visitors from other Spider-Verses arrive. The team moved from simulation-driven to design-driven effects, producing a fractured look — [fxphd](https://www.fxphd.com/fxblog/spider-verse-at-siggraph/) (search summary)
- Animators switched between animating on 1s and 2s to get a "stepped" look — [SideFX: Spider-Man: Into the Spider-Verse](https://www.sidefx.com/community/spider-man-into-the-spider-verse/) (search summary)
- Hobbyist recreation: split the R and G channels and offset them on the x-axis to get the chromatic-aberration look — [GarageFarm: Recreating the Spider-Verse look in Blender](https://garagefarm.net/blog/recreating-the-spider-verse-look-in-the-blender-node-editor)
- *Across the Spider-Verse* (2023) gives each universe its own art style; producers announced six distinct styles, e.g. an Indian comic-book look for Mumbattan (Earth-50101) — [AWN](https://www.awn.com/news/spider-man-across-spider-verse-feature-six-different-art-styles)
- SIGGRAPH 2023 talks:
  - "Non-photorealistic compositing of the Spider-Verse" (Davignon & St. Clair) notes the worlds "have wildly varying art styles and rules" — [SIGGRAPH history](https://history.siggraph.org/learning/non-photorealistic-compositing-of-the-spider-verse-by-davignon-and-st-clair/)
  - "Repainting the Spider-Verse" (Maccari, Grochola, Nicol, Blaškovič, Fapšo) describes a painting FX pipeline with Rebelle and Houdini — [SIGGRAPH history](https://history.siggraph.org/learning/repainting-the-spider-verse-by-maccari-grochola-nicol-blaskovic-and-fapso)
  - "Linework in Spider-Man: Across the Spider-Verse" — [SIGGRAPH history](https://history.siggraph.org/learning/linework-in-spider-man-across-the-spider-verse-by-grochola-maccari-lee-and-boulet-gilly)

**a-ha "Take On Me" (1985, dir. Steve Barron)**
- Live action was shot first, then hand-rotoscoped frame by frame into pencil-sketch animation by Michael Patterson and Candace Reckinger. Estimates range from more than 2,000 frames to "16 weeks" of work, and the sources conflict on exact counts. The idea came from Patterson's student short *Commuter* — [Wikipedia: Take On Me](https://en.wikipedia.org/wiki/Take_On_Me); [Irish Times: how we made Take on Me](https://www.irishtimes.com/culture/music/a-ha-how-we-made-take-on-me-and-the-famous-video-1.4064051); [befores & afters](https://beforesandafters.com/2020/02/20/a-has-rotoscoped-1985-music-video-for-take-on-me-has-been-watched-a-lot)
- It won six awards at the 1986 MTV VMAs and passed 1 billion YouTube views in February 2020 — [Wikipedia](https://en.wikipedia.org/wiki/Take_On_Me); [Classic Pop](https://classicpopmag.com/2020/02/a-ha-reaches-one-billion-views-on-youtube-with-take-on-me)
- An After Effects template exists to recreate the look, a sign that the effect is now a known meme format — [Cartoon Brew](https://www.cartoonbrew.com/tools/recreate-a-has-iconic-take-on-me-video-with-this-after-effects-template-207487.html)

**Everything Everywhere All at Once (2022, Daniels)**
- A core VFX team of about five people delivered close to 500 VFX shots, mixing digital and practical effects with no previs or storyboards. VFX supervisor Zak Stoltz discussed this with WIRED. One secondary source says the crew learned largely from free online tutorials (treat with caution) — [Slashfilm](https://www.slashfilm.com/825916/watch-how-vfx-brings-the-multiverse-of-everything-everywhere-all-at-once-to-life); [TheWrap](https://www.thewrap.com/everything-everywhere-all-at-once-vfx-supervisor-zak-stoltz-interview/); [No Film School](https://nofilmschool.com/everything-everywhere-all-at-once-visual-effects)

**Corridor Digital "Anime Rock, Paper, Scissors" (Feb 2023)**
- The Verge called it an over-the-top anime rendition of the game and said the making-of shows "the huge amount of work it takes to get this stuff right" — [The Verge, 27 Feb 2023 (via proxy)](https://hn.jakechampion.name/reader/https://www.theverge.com/2023/2/27/23616528/heres-how-to-make-an-ai-anime)
- Secondhand summaries say the team used Unreal Engine backgrounds plus compositing and lens effects to hold consistency. This is unverified — [Chaindesk summary of "Did We Just Change Animation Forever?"](https://chaindesk.ai/tools/youtube-summarizer/did-we-just-change-animation-forever-_9LX9HSQkWo)

**Washed Out "The Hardest Part" (dir. Paul Trillo, released 2 May 2024)**
- Billed as the first commissioned Sora music video with a major artist, it is one continuous forward-moving shot through a couple's life across eras — [No Film School](https://nofilmschool.com/ai-music-video); [Tom's Guide](https://www.tomsguide.com/ai/ai-image-video/i-cant-believe-openai-sora-made-this-trippy-new-music-video)
- fxguide reports about 700 generated clips; Tom's Guide says 55+ clips were used in the final edit — [fxguide](https://www.fxguide.com/?p=419437); [Tom's Guide](https://www.tomsguide.com/ai/ai-image-video/i-cant-believe-openai-sora-made-this-trippy-new-music-video)
- Stereogum disputes the "first" claim — [Stereogum](https://stereogum.com/?p=2261863)

**Split screens: (500) Days of Summer "Expectations vs Reality"**
- The screen is split into Tom's imagined party and what actually happens. The "reality" side slowly expands to take over the frame as he realizes the truth. Critics call it a "gut punch" rather than a gimmick — [Lipstick Letters](https://lipstickletters.substack.com/p/truth-and-perspective-in-500-days); [WWR Deep Dives](https://wwrdeepdives.substack.com/p/three-minutes-of-emotional-devastation)

### Inferences
**Spider-Verse style glitch kit (2–4 days, all NumPy/OpenCV on the existing person masks):**
1. **Style flicker on twos.** At 24 fps, hold each world for 2 frames (12 style changes/s), or switch on detected beats (librosa onset/beat tracking).
2. **Misregistration.** Shift the R and B channels of the person layer by ±k px. This works because the camera is fixed; in the source film, misregistration also stood in for depth of field.
3. **Halftone the person.** Make a dot screen from luminance, with hatching in the shadows.
4. **Slice glitch.** Displace random horizontal bands of the person mask and also the background plate near them. In the film, the glitch spreads to buildings and cars.
5. **Per-world people rules (Across the Spider-Verse "rules").** 1920s = sepia + grain + 18 fps step + gate weave; Van Gogh = on twos + brush texture; night = darker with neon rim light; cyberpunk = chromatic aberration + scanlines; winter = desaturated + breath/snow particles.

**Other borrowable transitions:**
- **Take On Me "reach across".** Stage a shot where someone extends a hand across the line and the hand becomes sketch or painting while the body stays real. It works because the line test is per pixel. An XDoG/edge-based "pencil" stylization of the person layer is cheap.
- **500 Days of Summer expanding split.** Animate the line itself: the boundary sweeps across the frame on the drop, so "reality" (or the other world) takes over. This is a beat-synced wipe the trailer can use.
- **EEAAO "verse-jump" montage.** Show the same person on the same footstep in 6 worlds, cut on 6 consecutive beats. This is cheap because all plates share geometry. Also cite EEAAO in the talk: 5 people, ~500 shots, as a reminder that clever constraints beat budget.
- **Trillo "endless push-in".** A digital zoom (crop) into the plate where each zoom step crosses into a new world (night → 1920s → winter → Van Gogh). This approximates a continuous journey without a moving camera.

### Gaps
- Could not fetch a primary Imageworks description of how the multiverse glitch transitions were built (shader/node level). Only summaries of fxphd/SideFX coverage were available; cartoonbrew.com and fxphd.com were blocked in this session.
- No source found for specific music videos that switch art style on every beat (beyond the general "style per universe" idea), and none for *Sliding Doors* split-screen technique.
- Corridor Digital's exact AI pipeline (models, settings) is unverified.

## 4. Computational photography demos that went viral or won awards (GauGAN, Everybody Dance Now, Real-Time Live, etc.)

### Takeaway
The demos people remember let the audience drive the input and see the output in seconds. GauGAN, a sketch-to-landscape demo co-created by a Berkeley student, won Best in Show and Audience Choice at SIGGRAPH 2019 Real-Time Live. Berkeley's own "Everybody Dance Now" spread through tech press within days because its side-by-side demo video was instantly legible. A live "pick your world, step across" kiosk follows the same recipe.

### Cited Findings
- **NVIDIA GauGAN**
  - Debuted at GTC in March 2019 as a sketch-to-photoreal-landscape tool running live on a TITAN RTX — [TechCrunch, 18 Mar 2019](https://techcrunch.com/2019/03/18/nvidia-ai-turns-sketches-into-photorealistic-landscapes-in-seconds/); [ServeTheHome: "perhaps the coolest GTC 2019 demo"](https://www.servethehome.com/nvidia-gaugan-perhaps-the-coolest-gtc-2019-demo/)
  - Won Best in Show and the (new that year) Audience Choice award at SIGGRAPH 2019 Real-Time Live. Berkeley EECS credits PhD student Taesung Park, who co-created it during an NVIDIA internship with Jun-Yan Zhu and NVIDIA researchers; credit lists vary by source — [NVIDIA blog](https://blogs.nvidia.com/blog/2019/07/30/gaugan-ai-painting); [Berkeley EECS news](https://eecs.berkeley.edu/news/gaugan-ai-art-tool-wins-two-major-awards-siggraph-2019-real-time-live-competition/); [SIGGRAPH history](https://history.siggraph.org/?p=90159)
- **Everybody Dance Now** (Caroline Chan, Shiry Ginosar, Tinghui Zhou, Alexei Efros, UC Berkeley; arXiv 22 Aug 2018; ICCV 2019) is "do as I do" motion transfer from a source dancer to an untrained target person in 2D video. Tech press covered it within days (TechXplore, 27 Aug 2018) and raised deepfake concerns — [arXiv 1808.07371](https://doi.org/10.48550/arXiv.1808.07371); [project page](https://carolineec.github.io/everybody_dance_now/); [TechXplore](https://techxplore.com/news/2018-08-neural-network-based-software-person.html)
- **SIGGRAPH Real-Time Live** precedents for live stylization:
  - 2020: Texler et al. shared Best in Show (tie) for interactive style transfer that learns an artist's style while they paint and applies it to a live video stream — [SIGGRAPH blog: AI Meets Artistry](https://blog.siggraph.org/2025/04/ai-meets-artistry.html/)
  - 2023: NVIDIA's generative-AI materials demo won Best in Show — [NVIDIA developer blog](https://developer.nvidia.com/blog/nvidia-research-shows-interactive-texture-painting-with-gen-ai-at-siggraph-asia-real-time-live/)
  - 2024: KREA Real-time was called a "standout" contribution, with no award confirmed in the source — [SIGGRAPH blog](https://blog.siggraph.org/2025/04/ai-meets-artistry.html/); [SIGGRAPH Real-Time Live page](https://siggraph.org/real-time-live)
- **Cinemagraphs** went from a 2011 Tumblr experiment to a widely used advertising format, an example of a simple compositing trick (still plate plus one moving region) becoming a genre — [Wikipedia: Cinemagraph](https://en.wikipedia.org/wiki/Cinemagraph); [Medium: Cinemagraphs in advertising](https://medium.com/new-media-photography/cinemagraphs-title-e47f9cf3b368)

### Inferences
- **The Real-Time Live format (presenter drives the demo live, under 6 minutes) is the model for our final presentation.** Run the kiosk live and let a classmate walk across the projected line, with a hotkey to switch worlds (GauGAN-style audience control). Keep the pre-rendered trailer as a fallback.
- **Everybody Dance Now's demo video is the template for our making-of.** It shows source, intermediate (pose) and output side by side. Our version: original, clean plate, restyled plate, masks, composite, as a 4-up grid or a "peel-away" layers animation.
- **Use the GauGAN/Berkeley lineage as framing.** Jun-Yan Zhu (CycleGAN's summer↔winter Yosemite, already cited in the proposal) and Taesung Park are Berkeley alumni, and Efros's group did Everybody Dance Now. The project sits in a Berkeley tradition, which is a nice line for the talk.

### Gaps
- Not verified in this session, though relevant: Deep Video Portraits (Kim et al., SIGGRAPH 2018), Google Pixel "Magic Eraser" (2021 launch), and the Matrix-era bullet-time rigs. No sources were fetched, so they are omitted from the findings.
- Did not identify the SIGGRAPH 2024 or 2025 Real-Time Live Best in Show winners, or any 2023–2026 Emerging Technologies piece that does live background restyling with people composited back.

## 5. Strong student course projects and how the best ones presented (CS180/CS194-26, CMU 16-726, Stanford, CS184)

### Takeaway
Berkeley CS194-26 (now CS180) final projects historically mix two "pre-canned" projects or a proposed custom project, and are presented as individual web pages under inst.eecs.berkeley.edu. The sister graphics course CS184 runs a formal showcase with winners and honorable mentions. Standout projects are typically self-contained web pages with embedded video, interactive comparisons and a clear failure-case section. A polished interactive page plus a short video is the expected bar, and a live demo would stand out.

### Cited Findings
- **CS194-26 final project format.** Students chose two of several pre-canned projects or proposed their own; custom projects required a proposal (Fall 2021), and grad CS294-26 students submitted a conference-style paper — [CS194-26 Fa21 final project](https://inst.eecs.berkeley.edu/~cs194-26/fa21/hw/final-project/); [Fa20 final project](https://inst.eecs.berkeley.edu/~cs194-26/fa20/hw/final-project/); [Fa16 final project](https://inst.eecs.berkeley.edu/~cs194-26/fa16/hw/final-project/); [Fa21 syllabus](https://inst.eecs.berkeley.edu/~cs194-26/fa21/upload/files/proj1/cs194-26-taa/CS%20194-26%20Syllabus.pdf)
- **Example student final-project pages**
  - "Vertigo Shot and Seam Carving" (Fa18) — [link](https://inst.eecs.berkeley.edu/~cs194-26/fa18/upload/files/projFinalAssigned/cs194-26-agc/)
  - "Getting Artsy with Computer Vision" (Fa21) — [link](https://inst.eecs.berkeley.edu/~cs194-26/fa21/upload/files/projFinalAssigned/cs194-26-ael/)
  - Other Fa17/Sp20 pages — [Fa17](https://inst.eecs.berkeley.edu/~cs194-26/fa17/upload/files/projFinalAssigned/cs194-26-abw/); [Sp20](https://inst.eecs.berkeley.edu/~cs194-26/sp20/upload/files/projFinalAssigned/cs194-26-aeo/)
- **CS180 Fall 2024.** The final project is required (pre-canned or own with a Gradescope proposal), and the page points students to the previous year's projects for inspiration. This comes from a search summary; the page could not be fetched — [CS180 Fa24 final project](https://cal-cs180.github.io/fa24/hw/fin_proj/index.html)
- **CS184 (Berkeley graphics)** runs a public showcase with Showcase Winners and Honorable Mentions. Spring 2025 had 60+ team projects, and a Fall 2026 showcase page exists — [CS184 Sp25 showcase](https://cs184.eecs.berkeley.edu/sp25/project/showcase); [CS184 Fa26 showcase](https://cs184.eecs.berkeley.edu/fa26/project/showcase/)
- **CMU 16-726 Learning-Based Image Synthesis** (Jun-Yan Zhu): students "build practical applications and create new visual effects using their own photos and videos." Course sites list offerings by year; example final project (Sp23): neural face relighting — [16-726 Sp24](https://learning-image-synthesis.github.io/sp24); [16-726 Sp23](https://learning-image-synthesis.github.io/sp23); [Sp23 final project example](https://www.andrew.cmu.edu/course/16-726-sp23/projects/gdr/index.html)

### Inferences
**Presentation checklist (inferred from these course formats plus the precedents above):**
1. A 60–90 s hero video (the trailer) at the top of the page.
2. An interactive before/after line slider and a world selector.
3. A pipeline figure with the 5 steps, each with a real intermediate image.
4. The seam metric with a zoomed crop of building edges before and after homography.
5. A failure gallery (shadows, reflections, people standing still that the median fails on, editor geometry drift).
6. If possible, the live kiosk at the presentation.

**Course-native techniques to fold in.** Several classic CS194-26 pre-canned options (seam carving, vertigo/dolly zoom, light fields) appear in example pages. A "vertigo zoom across the line" or a light-field-style refocus between worlds would show off course techniques inside the demo.

### Gaps
- Could not fetch cal-cs180.github.io (blocked in this session), so there is no list of past CS180 "best" final projects or of any CS180 showcase or awards.
- No Stanford CS231n/CS348 showcase pages were retrieved, and no source ranks "best" student computational-photography projects or documents what made them win.
