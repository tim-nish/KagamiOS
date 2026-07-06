# Questions

1. Is there an existing benchmark for graph-based literature exploration? If not, should we create one? If yes, which benchmark should KagamiOS/Scout target?

2. The Interviewer works well, but free-text answers are expensive for users. Would a multiple-choice + optional free-text format be a better design?

3. Once a literature map is built, can it be reused for future exploration, or should it always be regenerated?

4. Are there existing services that provide a literature exploration graph or research landscape? Or is this too dependent on individual interests and understanding? If commercial services exist, I'd like to know their approximate cost.

5. I think asking users to read papers or provide detailed opinions during the survey harms Kagami's value. Users start a survey because they do not yet understand the field. Would it be better to rely mainly on ratings, rankings, or simple choices instead of requiring free-text feedback?

6. Just to confirm: KagamiOS never has a phase where an agent reads an entire paper, correct? Full-paper reading is too expensive in tokens. If anything beyond the abstract is read, I want it to be limited to only the necessary sections.

7. Scout currently ends up processing around 200 papers in the corpus. Is reducing that expected to be part of the future optimization plan?

8. I'd like KagamiOS to distinguish between papers the user has already explored and new ones. Ideally, it should reuse previous maps and expand them from new perspectives instead of rebuilding everything. If this would significantly change the architecture, we can postpone the implementation.

9. Dogfooding currently reruns the entire pipeline from the beginning, which consumes too many tokens. Would it be straightforward to add a checkpoint/resume mechanism so execution can restart from the stage immediately before the modified component?
