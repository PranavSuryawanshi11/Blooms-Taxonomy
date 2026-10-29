# Revised Bloom's Taxonomy & Cognitive Calibration

BloomCraft AI implements the **Anderson & Krathwohl (2001) Revised Bloom's Taxonomy** across six hierarchical cognitive processing dimensions.

---

## 📊 Cognitive Processing Dimensions (L1–L6)

| Level | Cognitive Tier | Pedagogical Objective | Primary AICTE Action Verbs | Engineering Application Example |
| :---: | :--- | :--- | :--- | :--- |
| **L1** | **Remember** | Recall specific facts, definitions, terminology, and foundational principles. | *Define, State, List, Recall, Identify, Label* | State Amdahl's Law and identify its asymptotic boundary conditions. |
| **L2** | **Understand** | Construct meaning, translate representations, interpret graphs, and explain mechanisms. | *Explain, Describe, Illustrate, Summarize, Clarify* | Explain the working of the Backpropagation algorithm with chain rule derivatives. |
| **L3** | **Apply** | Execute a procedure or algorithm in a specified scenario or computational problem. | *Calculate, Apply, Implement, Solve, Execute* | Apply Dijkstra's algorithm to compute shortest path routing tables for a given topology. |
| **L4** | **Analyze** | Deconstruct systems into constituent parts, analyze trade-offs, and diagnose failures. | *Analyze, Differentiate, Compare, Deconstruct* | Analyze the cache hit ratio differences between direct-mapped and 4-way set-associative caches. |
| **L5** | **Evaluate** | Make critical judgments based on criteria, benchmarks, standards, and performance bounds. | *Assess, Justify, Appraise, Validate, Criticize* | Justify whether a CNN or Vision Transformer is more suitable for an edge IoT deployment. |
| **L6** | **Create** | Assemble elements to form a coherent, novel architecture, protocol, or design model. | *Design, Synthesize, Formulate, Construct* | Design an end-to-end fault-tolerant distributed consensus protocol under network partitions. |

---

## 🧮 Cognitive Index (CI) Mathematical Formulation

The system calculates a single scalar metric known as the **Cognitive Index ($\text{CI}$)** to quantify the overall academic rigor of an examination paper:

$$\text{CI} = \sum_{k=1}^6 k \times \left( \frac{\text{Marks}_{Lk}}{\text{Total Marks}} \right)$$

Where:
- $k \in \{1, 2, 3, 4, 5, 6\}$ represents the cognitive tier weight ($1$ for L1 up to $6$ for L6).
- $\text{Marks}_{Lk}$ is the sum of marks allotted to questions categorized at level $Lk$.
- $\text{Total Marks}$ is the maximum aggregate score of the question paper.

### Interpretation Guide:
- **$\text{CI} < 2.5$**: Foundational/Remedial tier (heavy on definitions and recall).
- **$2.5 \le \text{CI} \le 3.5$**: Balanced Undergraduate Engineering tier (aligned with AICTE reforms).
- **$3.5 < \text{CI} \le 4.5$**: Advanced / Autonomous Honours tier (heavy on application, analysis, and evaluation).
- **$\text{CI} > 4.5$**: Postgraduate / Research Examination tier (focus on evaluation and synthesis).

---

## 🎚️ Standard Cognitive Presets

| Preset | L1 (%) | L2 (%) | L3 (%) | L4 (%) | L5 (%) | L6 (%) | Target CI | Best Suited For |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **Balanced (AICTE Standard)** | 20% | 25% | 25% | 15% | 10% | 5% | **~2.85** | University End-Semester Examinations |
| **Application Heavy** | 10% | 20% | 40% | 20% | 5% | 5% | **~3.25** | Practical & Lab-Integrated Theory Courses |
| **Foundational / First Year** | 35% | 35% | 20% | 10% | 0% | 0% | **~2.05** | First-Year Engineering / Core Science |
| **Autonomous Honours** | 10% | 15% | 25% | 25% | 15% | 10% | **~3.60** | Autonomous Institutes (e.g. RCPIT, DJSCE) |
| **Research / M.Tech** | 5% | 10% | 20% | 30% | 20% | 15% | **~4.05** | Master of Technology & Specialization Electives |
