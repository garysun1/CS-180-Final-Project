# Demo and Presentation Design for "Cross the Line" (CS180 Final Project)

## 1. Live tech demo design and risk management (rehearsal, fallbacks, offline, latency, golden path)

### Takeaway
Experienced presenters rarely bet a short slot on a live demo. Make the pre-recorded video the main event in the presentation slot, and keep the live webcam demo as an extra for the poster session. That demo should run offline on a fixed "golden path" of steps rehearsed until they are boring, with a backup that is already loaded and can be switched to in one keystroke.

### Cited Findings
- **Startup demo days have largely dropped live demos.** YC's own guide says "demos seldom work in modern demo day presentations" — [YC, A Guide to Demo Day Presentations (Ralston)](https://www.ycombinator.com/blog/guide-to-demo-day-pitches/). Paul Graham notes the presentations are "so short that they rarely include much if any demo" and advises: "start with the problem you're solving, and then show how your product solves it" rather than "a catalog of features" — [Paul Graham, How to Present to Investors](https://paulgraham.com/investors.html).
- **Justin Kan (YC alum):** "Don't do a demo. Demos break. If your product is truly that amazing, show a video, and interested audience members will clamor for a demo afterwards." — [Justin Kan, How to pitch your startup on stage](https://justinkan.com/feed/how-to-pitch-your-startup-on-stage)
- **Short clip early.** A third-party pitch guide (a vendor blog, not official YC advice) recommends a 10–15 s clip of the product working on slide 1 or 2, and launch videos under about 60 s — [Flowjam](https://www.flowjam.com/blog/yc-demo-day-presentation-format-15-slide-script-that-wins-checks)
- **The "golden path" (2007 iPhone keynote).** Engineers found, through hours of trial and error, a specific set of tasks done in a specific way and order that would get the prototype through the keynote without crashing. This is the original "golden path" — [MacRumors summary of Fred Vogelstein's NYT account](https://www.macrumors.com/2013/10/04/former-apple-engineer-gives-behind-the-scenes-look-at-the-original-iphone-introduction/). Even on that path, the phone could play part of a song or video but not a whole clip reliably — [Kottke excerpt of Vogelstein](https://kottke.org/13/10/part-of-the-untold-iphone-story). Additional color: [9to5Mac](https://9to5mac.com/2017/01/09/steve-jobs-iphone-presentation-2007-inside-story/). Caveat: a claim that Jobs rehearsed five days straight appears only in secondary accounts. Some blogs call the demo "faked", which overstates Vogelstein's reporting.
- **SIGGRAPH Real-Time Live! practice.** Presenters may show only jury-accepted content and no new material. In 2023 there was a mandatory rehearsal of the whole program on show morning, plus check-in and tech setup the day before, which all presenters had to attend — [SIGGRAPH 2023 Real-Time Live!](https://s2023.siggraph.org/program/real-time-live). Conditionally accepted work had to be shown to a juror by video to verify the real-time claim — [SIGGRAPH 2022 Real-Time Live!](https://s2022.siggraph.org/program/real-time-live/). Recent show recaps: [SIGGRAPH 2025 RTL recap](https://blog.siggraph.org/2025/08/siggraph2025-real-time-live-12-groundbreaking-demos.html/), [SIGGRAPH 2026 RTL](https://blog.siggraph.org/2026/07/watch-it-work-real-time-live-2026-brings-emerging-technology-to-the-stage-in-la.html/).
- **Keep the backup in exactly the same state.** Microsoft's event-demo team says the backup kit must be "in exactly the same state your primary kit was in" so the switch is seamless, and suggests a backup machine already connected — [Microsoft, How we demo](https://learn.microsoft.com/en-my/archive/blogs/cjohnson/how-we-demo)
- **Practitioner consensus.** The search summary did not cleanly attribute each point to one post, so the sources below are listed as a cluster:
  - Record a backup video in advance.
  - Use layered fallbacks: live, then pre-recorded video, then screenshots.
  - Make each demo step independent so one failure doesn't sink the rest.
  - Don't debug on stage; switch to the backup unless the fix is trivial.
  - Use demo infrastructure that does not need internet. Common failures are network outages, exceeded quotas and expired licenses.
  - When something breaks, stay calm and use light humor.

  Sources: [Redgate Simple Talk, How to avoid demo fails](https://www.red-gate.com/simple-talk/?p=111618); [Productside](https://productside.com/?p=15049); [Reprise, failing forward](https://www.reprise.com/resources/blog/the-art-of-failing-forward-demo-lessons-learned); [thebeebs, reasons your demos will fail at a conference](https://github.com/thebeebs/thebeebsContent/blob/master/reasons-your-demos-will-fail-at-a-conference.md); [Oracle-Base, live demonstrations](https://oracle-base.com/blog/2014/01/05/public-speaking-tip-7-live-demonstrations/); [Murphy's law meets demo day](https://ramperry.substack.com/p/when-murphys-law-meets-demo-day).
  - Counterpoint: one commenter argues that video demos are less engaging and can't answer questions on the fly, so a backup should supplement a live demo, not replace it (same cluster).
- **Latency budget anchors (Nielsen's three limits):**
  - About 0.1 s: feels like direct manipulation, and no feedback is needed beyond showing the result.
  - About 1 s: keeps the user's train of thought.
  - About 10 s: the limit for holding attention.

  Nielsen notes the exact limits vary by context; the idea traces back to Miller (1968) — [NN/g, 3 response-time limits](https://www.nngroup.com/videos/3-response-time-limits-interaction-design/); [NN/g website response times](https://www.nngroup.com/articles/website-response-times/)

### Inferences
- **Why Cross the Line suits a live demo.** The background is static, so the expensive step (restyling the clean plate with FLUX/Qwen/SDXL) can be precomputed offline for every effect. The live loop then only needs person segmentation, compositing and an optional per-person style match. That is a far lighter real-time load than generative video, and it removes all network and API dependence on demo day.
  - Keep all model weights local.
  - Precompute the clean plate and the restyled plates for the poster-session location ahead of time. Capture the clean plate at that exact spot about 10 minutes before opening, and re-run the median if the lighting changes.
- **Latency targets** (derived from Nielsen):
  - The live mirror should update in roughly 100 ms or less end to end. Aim for ≥10–15 fps, because the line-crossing "pop" must feel instantaneous.
  - Switching effects can take up to about 1 s.
  - Anything heavier, such as generating a new style from a typed prompt, must show progress and finish within about 10 s, or move it off the live path entirely.
  - If segmentation can't hit about 10 fps on the laptop, downscale the input (e.g., 480p for the mask, upsampled for compositing) rather than let the frame rate drop.
- **Define a golden path for the 5-minute slot.** One scripted sequence:
  - a teammate walks across the line in Real mode;
  - switch to "Night", then "1920s", then "Painting";
  - drag the line;
  - optionally show depth mode.

  Rehearse it at least 5 times on the exact laptop, display adapter and room lighting. Every other feature is off the golden path and only shown when asked.
- **Fallback ladder** (each level ready before you start):
  1. live webcam;
  2. the same app replaying a recorded webcam clip through the identical pipeline. This looks "live" and is honest if you say "here's a recording run through the same code";
  3. the trailer MP4 stored locally, not streamed from YouTube;
  4. stills and GIFs in the slides.

  Bind the switch to a single hotkey, and never debug on stage.
- **Pre-flight checklist:**
  - Offline mode: wifi off during the rehearsal run.
  - Laptop power: plugged in, high-performance mode.
  - Interruptions: notifications and auto-updates off.
  - Camera: exposure, white balance and focus locked, mirroring the project's own capture rule.
  - Hardware: a spare USB webcam and a USB-C to HDMI adapter.
  - Tripod: taped floor mark for its position.
  - The line itself: taped on the floor so it is visible in both the room and the frame.
- **Honesty requirement.** Label pre-recorded material as such, e.g. "recorded run, same pipeline". This matches the course's emphasis on honest reporting, and Real-Time Live!'s rule of showing only verified real-time work.

### Gaps
- Could not retrieve full text of several primary sources (www.cs.columbia.edu "Hints for Presenting Demos" by Henning Schulzrinne; fxguide's behind-the-scenes on SIGGRAPH Asia Real-Time Live!; distill.pub). Those hosts are blocked by this session's network policy, so the per-demo time limit at Real-Time Live! (commonly cited as a few minutes per team) is unverified here.
- No source found on Google I/O keynote demo practices specifically; MLH demo advice not retrieved.

## 2. Research project websites that work well (templates, interactive elements, accessibility, load time)

### Takeaway
Start from the Nerfies-lineage template. Put the trailer at the top, and make the drag-the-line comparison the centerpiece, built on a native `<input type="range">` so it works with touch, keyboard and screen readers. Each interactive element should guide attention to one specific phenomenon, as in Bret Victor's "explorable explanations", rather than be a free-floating widget.

### Cited Findings
- **Templates.** The de facto standard CV/graphics project page comes from Keunhong Park's Nerfies page.
  - Eliahu Horwitz's Academic Project Page Template is a Nerfies derivative: "Use this Template", deploy on GitHub Pages — [GitHub: eliahuhorwitz/Academic-project-page-template](https://github.com/eliahuhorwitz/Academic-project-page-template)
  - Other derivatives: an Astro/Tailwind port ([astro.build theme](https://astro.build/themes/details/academic-project)) and vinthony's template, with teaser video, image carousel, YouTube embed, video carousel and PDF poster blocks under CC BY-SA 4.0 ([vinthony/project-page-template](https://www.github.com/vinthony/project-page-template)).
  - The original Nerfies page uses Google Sans, which is licensed by Google, so derivatives often swap the font — [awesome-project-homepage-template list](https://awesome.ecosyste.ms/projects/github.com%2Fwangrongsheng%2Fawesome-project-homepage-template).
- **Explorable explanations (Bret Victor, 2011)** popularized "reactive documents", where readers manipulate the author's assumptions and see the consequences. These differ from isolated widgets because they deliberately guide the audience's attention to particular phenomena — [Victor, Explorable Explanations](https://worrydream.com/ExplorableExplanations/); [Wikipedia: Explorable explanation](https://wikipedia.com/wiki/Explorable_explanation)
- **Hohman, Conlen, Heer & Chau (Distill, 2020), "Communicating with Interactive Articles"** synthesizes education, journalism and visualization research — [UW IDL page](https://idl.uw.edu/papers/comm-interactive-articles). Course slides summarizing it list these affordances: connecting people and data, making systems playful, promoting self-reflection, personalizing reading and (in some versions) reducing cognitive load — [UW CSE442 Narrative slides](https://courses.cs.washington.edu/courses/cse442/22wi/lectures/CSE442-Narrative.pdf). The paper's quantitative engagement findings could not be retrieved; see Gaps.
- **Accessible before/after sliders.**
  - A native range input supports touch dragging and arrow keys out of the box, and works with VoiceOver and TalkBack.
  - You can hide it visually (opacity 0) and draw a custom handle, but you must give the handle a visible focus outline and add an accessible label.
  - Libraries add Home/End jumps and Shift+arrow 10% steps.
  - An alternative is `role="slider"` with `aria-valuemin`/`aria-valuemax`/`aria-valuenow` and `tabindex`.

  Sources: [romaintrotard.com comparison component](https://romaintrotard.com/posts/comparison-component); [img-comparison-slider README](https://cdn.jsdelivr.net/npm/img-comparison-slider@8.0.7/README.md); [react-comparison-slider](https://github.com/mattrothenberg/react-comparison-slider); [Reuters graphics BeforeAfter](https://cdn.jsdelivr.net/npm/@reuters-graphics/graphics-components@4.7.0/dist/llm-docs/components/BeforeAfter.md)

### Inferences
- **Recommended page order** for Cross the Line:
  1. Title and one-sentence hook ("Step across the line into another world").
  2. Autoplaying, muted, looping trailer above the fold (≤60 s cut).
  3. The interactive drag-the-line player: a video with the line position bound to a range input. This is the explorable that teaches the central idea: the background is restyled once, people are pasted back, so the restyled half cannot flicker.
  4. Effect gallery (season, night, century ago, painting).
  5. "How it works" pipeline figure, with clean plate, then restyle, then align, then SAM mask, then composite.
  6. Baseline comparison, synchronized side by side (see §5).
  7. Depth slider (stretch result).
  8. A Failure cases section.
  9. Write-up/report link and credits.
- **Guide attention with each control.** The drag-the-line slider should open on a frame where a person is mid-crossing, so the effect is visible on first interaction. A caption should tell the viewer what to look for, e.g. "drag the line through the Campanile — edges should not jump". That is Victor's "guide attention" principle applied.
- **Load time** (general web practice, not retrieved from a source here):
  - Give every video a `poster` image, and use `preload="metadata"` and lazy loading for gallery items.
  - Encode H.264 MP4 at 1080p or below for the web, with short loops.
  - For "loading" comparisons, use the same encoded resolution on both sides so compression artifacts don't bias the viewer.
  - Use `muted playsinline` so autoplay works on iOS.
  - Test the page on a phone over cellular, because poster-session visitors will scan a QR code.
- **Accessibility minimums:** labeled sliders; captions on the trailer; alt text on figures; don't encode meaning in color alone; and a non-interactive fallback (static before/after pairs) for visitors who don't touch the controls.

### Gaps
- No primary measurements found on which project-page elements (teaser vs slider vs gallery) researchers or visitors actually engage with. The Distill paper's engagement statistics could not be fetched (distill.pub blocked).
- No retrieved source for Two Minute Papers' format conventions, or for Jon Barron's/Keenan Crane's presentation advice. Their own sites were not reachable or not searched within budget.
- Web-video encoding and lazy-loading recommendations above are standard practice but uncited here.

## 3. Video/trailer storytelling (fast-forward conventions, structure, pacing, captions, music licensing)

### Takeaway
Produce two cuts: a 20–30 s "fast-forward" hook and a 2–3 min main video (SIGGRAPH's Thesis Fast Forward caps at 3 min, 1080p, 30 fps). Lead with the wow shot, explain the method in one visual beat, show results and the baseline, and close with the "how each shot was made" segment. Get music from YouTube Audio Library or Pixabay, and check each track's license.

### Cited Findings
- **SIGGRAPH formats:**
  - Thesis Fast Forward: maximum 3 minutes, 1920×1080, 30 fps (2027 page; 2026 and 2024 calls also used 3 minutes) — [SIGGRAPH Thesis Fast Forward 2026](https://research.siggraph.org/programs/thesisff-2026/)
  - Technical Papers Fast Forward: a 20-second pre-recorded video for 2023; the 2026 author instructions describe both 10-second and 20-second variants — [SIGGRAPH 2026 Papers Fast Forward author instructions](https://s2026.siggraph.org/papers-fast-forward-author-instructions/)
  - Posters (2021): a 30-second fast-forward — [SIGGRAPH 2021](https://s2021.siggraph.org/?p=781)
- **Hackathon judging norms.**
  - Video limits run about 2–5 minutes, and one event warns judges may not watch past 2 minutes.
  - Production polish matters less than showing an impressive working demo.
  - Open with motivation and a 30-second pitch of why it's useful; include a try-it link; explain the technical approach and why.

  Sources: [hackathon.com tips](https://tips.hackathon.com/article/creating-the-best-demo-video-for-a-hackathon-what-to-know); [HackHCC judging guide](https://hackhcc.gitbook.io/hackhcc-docs/other-resources/submission-and-judging-guide); [DEV: How to make your Devpost submissions not suck](https://dev.to/jacklynbiggin/how-to-make-your-devpost-submissions-not-suck-37i0)
- **Lead with the problem, not features** — [Paul Graham](https://paulgraham.com/investors.html)
- **Music licensing:**
  - **YouTube Audio Library:** most tracks need no attribution. A subset marked CC BY requires crediting the artist and linking the track in the description; check the "License type" column in YouTube Studio — [vidIQ on YouTube Audio Library](https://vidiq.com/blog/post/royalty-free-music-youtube-audio-library/)
  - **Pixabay Music:** described as usable in videos without attribution. Sources conflict on whether tracks are CC0 or under Pixabay's own Content License, so check the track page — [Hello Thematic](https://hellothematic.com/best-free-music-websites/); [moonb.io](https://www.moonb.io/blog/non-copyright-music-sites)
  - **Free Music Archive:** mixes CC0, CC BY and CC BY-NC, so check each track's tag — [Hello Thematic](https://hellothematic.com/best-free-youtube-music-websites/). Student copyright guidance: [CUNY Hostos copyright for students](https://guides.hostos.cuny.edu/copyright-for-students/using-others-work); [SUNY Open Media Lab](https://online.suny.edu/openmedialab/?p=87)

### Inferences
- **Suggested 2:30 main-video structure:**

  | Time | Beat | Content |
  |---|---|---|
  | 0:00–0:10 | Cold open | Wow shot: someone walks through Sather Gate and turns 1920s sepia as they cross. No title card first. |
  | 0:10–0:25 | Problem | Per-frame restyling flickers and buildings wobble. A 3 s side-by-side of a naive per-frame restyle vs. the method. |
  | 0:25–0:55 | Method | One animated diagram: median clean plate, restyle once, align (homography), SAM 3 masks plus shadow ratio, composite. |
  | 0:55–1:50 | Results montage | One landmark per effect, about 8–10 s each, cut on line-crossings. |
  | 1:50–2:15 | Evaluation and failures | Seam-jump numbers, failure clips. |
  | 2:15–2:30 | Credits | "How it's made" outro, credits with music attribution. |

  The 20–30 s fast-forward is the cold open, the problem split-screen and two result shots.
- **Pacing and captions:**
  - Cut on the crossing moment; that is the money frame.
  - Burn in short on-screen labels ("per-frame baseline", "ours", "real ↔ restyled") so the video works muted at a poster session.
  - Add a caption track (SRT) for the online version.
  - Keep the method beat visual; avoid equation slides.
- **Licensing hygiene.** Keep a credits file listing each track title, artist, source URL and license. YouTube Audio Library "no attribution" tracks are the lowest-risk choice; avoid FMA tracks marked NC-ND if you edit or cut them.

### Gaps
- Could not retrieve SIGGRAPH's technical-papers *supplementary video* guidelines (as distinct from fast-forward), or authoritative pacing guidance for research videos. The structure above is synthesized, not sourced.
- Pixabay's exact current license terms are inconsistently described in secondary sources; the primary license page was not fetched.

## 4. Interactive installation / poster-session engagement (participation, throughput, shareable output, privacy/consent, signage)

### Takeaway
Public-display research shows that people are drawn in by watching others interact (the "honeypot effect"), and that passers-by often notice interactivity too late. So the screen should face the walkway, a teammate should "seed" the interaction by crossing the line, and the call to action should be visible from a distance ("Walk across the tape →"). Pair it with clear signage that the camera is live and, by default, nothing is recorded. Make sharing (GIF/QR) strictly opt-in.

### Cited Findings
- **Honeypot effect.** People interacting with a public display attract others. The current user is the key mediator: without someone already interacting, the effect does not occur — [Frontiers in VR 2025 honeypot study](https://public-pages-files-2025.frontiersin.org/journals/virtual-reality/articles/10.3389/frvir.2025.1714725/epub); [Alt, 2013 dissertation](https://www.rz.unibw-muenchen.de/usable-security-and-privacy/publikationen/pdf/alt2013diss.pdf)
- **Audience funnel model.** Stages run: passing by, then viewing and reacting, subtle interaction, direct interaction, multiple interaction, and follow-up actions — [Alt 2013](https://www.rz.unibw-muenchen.de/usable-security-and-privacy/publikationen/pdf/alt2013diss.pdf)
- **Landing effect and queueing.** In a lab and shop-window field study (502 sessions), passers-by often noticed interactivity late and had to walk back to interact. When someone was already interacting, others lined up behind them in rows — [Dürr, Noticing Interactivity of Public Displays (LMU)](https://www.mmi.ifi.lmu.de/lehre/ss15/ps/papers/Duerr-NoticingInteractivity.pdf)
- **Crowds can inhibit.** The more passive audience members present, the farther away users position themselves. High audience numbers and close spectators increase user–display distance and reduce interaction time — [Gentile, Khamis, Sorce & Alt, PerDis 2017](https://www.medien.ifi.lmu.de/pubdb/publications/pub/gentile2017perdis/gentile2017perdis.pdf)
- **Display geometry.** Flat display layouts triggered the strongest honeypot effect, compared with hexagonal or concave layouts — [Chained displays study](https://typeset.io/pdf/chained-displays-configurations-of-public-displays-can-be-3qr69ccilw.pdf)
- **Posted consent signs can work.** In museum research on trilingual posted signs at recording areas, 75% of visitors leaving the area had read and understood the signs. A follow-up with 255 adults tested six signage and setup variants — [InformalScience, Gaining Visitor Consent III](https://www.informalscience.org/gaining-visitor-consent-research-iii-trilingual-posted-sign-method)
- **Installation privacy patterns:**
  - Edinburgh Inspace's camera installation posts a notice that cameras capture a live feed and that nothing is recorded or stored, and it links its data-protection impact assessment — [Inspace](https://inspace.ed.ac.uk/?p=4388).
  - *I & AI: Mirror* lets visitors withdraw consent and request data removal during the exhibition — [Inspace privacy statement](https://inspace.ed.ac.uk/?p=6084).
  - *Wave at First Sight* auto-blurs detected people using pose detection — [Images Out of Control](https://images-out-of-control.kleio.com/4_2024/22_wave-at-first-sight).
  - Interviewed immersive-art practitioners stress opt-in systems for transparency and consent — [arXiv 2407.05450](https://ar5iv.labs.arxiv.org/html/2407.05450).

### Inferences
- **Layout:**
  - Put the laptop or an external monitor flat-facing the aisle, with the camera visibly mounted on its tripod next to it.
  - Tape the line on the floor in a bright color, aligned with the in-frame line, so the physical and virtual lines match. This is self-explanatory and supports instant gratification.
  - Put a large sign readable at about 3 m: "Cross the line → step into 1925".
- **Seed the honeypot.** A teammate crosses back and forth when the booth is idle, because the effect needs a visible user. When a crowd forms, step the spectators back to the side (Gentile et al.) so the walker has room.
- **Throughput.** One crossing takes about 3–5 s, so a single camera can serve a queue quickly. Let each visitor pick the world (a button or keyboard shortcut on a "world picker" card) to add agency. The live mirror should respond in under 100 ms (see §1).
- **Shareable output.** Offer an opt-in "Save my crossing" button. It makes a 3 s GIF/MP4 available via a QR code that links to a temporary page; delete those clips after the session. Default behavior is display-only with no recording, stated on the sign.
- **Signage text (suggested):** "Live camera. Nothing is saved unless you press SAVE. Saved clips are deleted after today. Want to be blurred? Ask us." Also offer a "blur me" toggle: SAM masks make it trivial to blur or pixelate only people.
- **Course footage.** For the course video, get verbal or written OK from identifiable people who were filmed. For incidental passers-by on campus, consider blurring faces or using clips where people are small, to avoid ethical issues in published media.

### Gaps
- No authoritative UC Berkeley policy on filming members of the public for course projects was retrieved. Legal requirements vary by jurisdiction; consult course staff or campus guidance.
- No retrieved study quantifying the uplift from QR or shareable-GIF calls to action at poster sessions.

## 5. Presenting evaluation, metrics and failures engagingly

### Takeaway
Show evaluation as synchronized side-by-side video against a per-frame restyling baseline, backed by one or two simple numbers. Use the project's seam edge-jump in pixels, plus a flow-based warping error à la Lai et al. 2018, paired with a perceptual metric because warping error alone rewards blur. Give failures their own short, labeled section ("what broke and why"), which the course explicitly values.

### Cited Findings
- **Warping error (Lai et al., ECCV 2018).** Temporal stability is measured by warping frame t+1 to frame t with optical flow and computing masked squared differences on non-occluded pixels, averaged over the video. It is paired with an LPIPS-style perceptual distance to the per-frame processed output, because a blurry video gets low warping error but high perceptual distance — [Lai et al., arXiv 1808.00449](https://arxiv.org/pdf/1808.00449); [supplementary](https://jbhuang0604.github.io/supp/ECCV_2018_VideoConsistency_Supp.pdf)
- **Caveats on warping error:**
  - It inherits optical-flow errors and can be masked by blurring — [BlazeBVD, arXiv 2403.06243](https://arxiv.org/pdf/2403.06243).
  - LPIPS-based perceptual metrics miss localized style deviations and brightness changes — [arXiv 2103.07278](https://arxiv.org/pdf/2103.07278).
  - Deep Video Prior computes warping error against both the previous frame and the first frame, to capture short- and long-term consistency — [arXiv 2010.11838](https://arxiv.org/pdf/2010.11838).

### Inferences
- **Headline comparison.** Use a three-column synchronized clip, all with the same people pasted back:
  1. per-frame image restyle (same editor, same prompt);
  2. a commercial or research video restyler, if available;
  3. ours.

  Report background warping error for each. Ours is near zero by construction because the background is one still, so say so explicitly and don't over-claim. The interesting number is the baseline's error. The honest framing: "near-zero by construction; the trade-off is no camera motion and no scene-reactive lighting."
- **Make the seam metric visual.** Show a zoomed crop where a building edge crosses the line before and after alignment, with the measured jump in pixels annotated. A short bar chart across landmarks and editors (FLUX.2 Klein vs Qwen-Image-Edit vs SDXL+ControlNet) gives the "which editor preserves geometry" result at a glance.
- **Flicker visualization.** An x–t slice (one pixel row stacked over time) makes flicker visible as a still image: the baseline shows streaky noise, ours shows clean vertical stripes. This is a compact poster figure. It is a standard video-processing visualization, but no source was retrieved here.
- **Identity check (from the proposal).** Compositing the people onto the *unedited* clean plate should reproduce the original footage. Report PSNR or difference maps, and show the residual where shadows or mask edges fail.
- **Small user study.** A two-alternative forced-choice test with about 10 classmates ("which looks more stable / more like a real place?") over 6–10 randomized clip pairs. Report it as a preference percentage with n, and state it is informal. Label the sample size honestly.
- **Failure gallery.** Show 3–5 GIFs with one-line causes:
  - people standing still get absorbed into the median plate;
  - shadows or reflections crossing the line;
  - editors hallucinating new geometry;
  - SAM mask holes on bikes or umbrellas;
  - lighting mismatch, e.g. a sunlit person in a night scene.

  Put this on the website and give it one slide or poster panel. It builds credibility and pre-empts the hardest questions.

### Gaps
- No retrieved source for best practices on informal classmate user studies (sample size, 2AFC design) in course contexts, or for the x–t slice visualization. These recommendations are based on general practice, not sources found here.
