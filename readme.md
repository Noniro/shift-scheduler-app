# Shift Scheduler Application

A sophisticated web-based employee scheduling system that uses **fair-share algorithms** to automatically generate balanced work schedules. The application considers worker qualifications, availability constraints, individual difficulty perceptions, and workload distribution to create equitable schedules.

## 🎯 Project Overview

The Shift Scheduler solves the complex problem of **fair shift assignment** in organizations where:
- Workers have different skill sets and qualifications
- Jobs have varying levels of difficulty
- Workers have availability constraints (vacations, appointments)
- Fairness and work-life balance are priorities

Unlike simple round-robin schedulers, this application uses **algorithmic fairness concepts** from economics to ensure that workload distribution is perceived as fair by all workers, taking into account their individual difficulty ratings.

---

## 🧮 Algorithm Explanation

### Core Algorithm: Weighted Greedy Assignment

The scheduling algorithm is a **greedy algorithm with dynamic weighted hours calculation** that prioritizes fairness over simple optimization. Here's how it works:

#### 1. **Weighted Hours System**

Instead of treating all shifts equally, the algorithm uses a **weighted hours** metric:

```
Weighted Hours = Real Hours × Difficulty Rating
```

**Example:**
- An 8-hour "Easy" shift (difficulty 1.0) = 8 weighted hours
- An 8-hour "Very Hard" shift (difficulty 5.0) = 40 weighted hours

This ensures that workers assigned to difficult roles don't get overworked.

#### 2. **Individual Difficulty Perception**

The system supports **worker-specific difficulty ratings**:
- Workers rate each job role from 1-5 based on their personal perception
- The algorithm uses these individual ratings (not just averaged ratings)
- Formula: `hybrid_difficulty = α × base_difficulty + (1-α) × individual_rating`
  - Default α = 0.5 (50% objective, 50% subjective)

**Why this matters:** A role that's "hard" for one worker might be "easy" for another with more experience.

#### 3. **Greedy Assignment Process**

For each shift slot (sorted by start time):

1. **Filter eligible workers:**
   - Check role qualification
   - Check availability (no constraint conflicts)
   - Check for overlapping shifts
   - Check max hours limit

2. **Calculate effective weighted hours** for each eligible worker:
   ```
   effective_weighted_hours = current_weighted_hours × role_penalty
   ```
   - `role_penalty` discourages assigning the same role consecutively (2.0x penalty for yesterday, 1.5x for 2 days ago, etc.)

3. **Sort workers by effective weighted hours** (ascending):
   - Workers with fewer weighted hours get priority
   - Random tie-breaking for fairness

4. **Assign to the worker with lowest weighted hours:**
   - Update their real hours
   - Update their weighted hours using their individual difficulty rating
   - Record the assignment

#### 4. **Fairness Guarantees**

The algorithm aims to achieve:

- **Proportional Share:** Each worker gets ≥ 1/n of total workload (in their perception)
- **Envy-Free (EF):** No worker prefers another's assignment bundle

These are concepts from **algorithmic fair division** and ensure that the schedule is perceived as fair even when workers have different preferences.

#### 5. **Key Algorithm Features**

✅ **Randomization with Seeds:** Each generation randomizes worker order and shift processing for variety while maintaining reproducibility
✅ **Role Rotation:** Penalty system prevents workers from getting stuck in the same role
✅ **Time Restrictions:** Supports roles that only work specific hours (e.g., night shifts: 22:00-06:00)
✅ **Constraint Handling:** Full-day and specific-hour unavailability
✅ **Comprehensive Logging:** Detailed execution logs for transparency and debugging

---

## ✨ Key Features

### Scheduling Management
- 📅 **Multiple Scheduling Periods:** Create separate schedules for different weeks/months
- 👥 **Worker Management:** Add workers with qualifications, max hours, and unavailability
- 🎭 **Job Role Definition:** Define roles with duration, worker count, and time restrictions
- 📊 **Fair Assignment:** Automated greedy algorithm with fairness guarantees

### Advanced Difficulty System
- ⚖️ **Worker Rating System:** Workers democratically rate job difficulty (1-5 scale)
- 📋 **CSV Template Export:** Generate rating templates in matrix format (workers × roles)
- 📊 **Consensus-Based Ratings:** Average worker ratings determine role difficulty
- 🛡️ **Gaming Prevention:** Detects and removes extreme rating patterns (all 1s or all 5s)

### Fairness Analytics
- 📈 **Fairness Statistics Dashboard:** Visualize proportional share, envy-free, and EF1 metrics
- 👤 **Individual Worker Analysis:** See each worker's fairness properties
- 📊 **Workload Distribution Charts:** Bar charts, pie charts, and comparative visualizations
- 🌙 **Night/Weekend Tracking:** Monitor distribution of undesirable shifts

### Export & Logging
- 💾 **CSV/Excel Export:** Download schedules in standard formats
- 🔍 **Algorithm Logs:** View detailed step-by-step execution logs
- 📋 **Constraint Summaries:** Track worker availability and assignments

---

## 🚀 Installation & Setup

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)
- Git (optional, for cloning)

### Step 1: Clone or Download

```bash
# Clone the repository
git clone https://github.com/your-username/shift-scheduler.git
cd shift-scheduler

# Or download and extract the ZIP file
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Initialize Database

```bash
# Initialize migration repository (first time only)

python -m flask db init

# Create initial migration
python -m flask db migrate -m "Initial migration"

# Apply migration
python -m flask db upgrade
```

### Step 4: Run the Application

```bash
# Option 1: Using run.py (opens browser automatically)
python run.py

# Option 2: Using Flask command
flask run

# Option 3: Custom host/port
python run.py --ip 0.0.0.0 --port 8080
```

The application will be available at `http://127.0.0.1:5000`

---

## 📖 How to Use the Application

### 1. **First Time Setup**

#### Set Your Name
- On first visit, enter your name (stored in session)
- This personalizes your experience

#### Create a Scheduling Period
1. Navigate to **"Scheduling Periods"** in the menu
2. Click **"Create New Scheduling Period"**
3. Fill in:
   - **Period Name:** e.g., "Restaurant Weekly Rota - Jan 2025"
   - **Start Date/Time:** Select date range (uses date picker)
   - **End Date/Time:** Period end
4. Click **"Create Period & Define Roles"**

### 2. **Define Job Roles**

After creating a period, you'll be redirected to define job roles:

1. **Add a Job Role:**
   - **Role Name:** e.g., "Cook", "Server", "Manager"
   - **Number Needed:** How many workers simultaneously (e.g., 2 cooks)
   - **Shift Duration:** Days, hours, minutes (e.g., 8 hours)
   - **Working Hours (Optional):**
     - Check "Restrict Working Hours" for time-specific roles
     - Example: Night Guard (22:00 - 06:00, overnight shift)
   
2. **Note:** Initial difficulty is neutral (1.0) until workers rate it

3. **Repeat** for all roles in your organization

### 3. **Add Workers**

Navigate to **"Manage Workers"**:

1. **Add New Worker:**
   - **Name:** Worker's full name
   - **Email:** (Optional) for notifications
   - **Max Hours:** Maximum hours per period (optional)
   - **Qualified Roles:** Select which roles this worker can perform

2. **Add Unavailability:**
   - Click **"Add Unavailability"** next to worker name
   - Choose **Full Day** (vacation) or **Specific Hours** (appointment)
   - Example: Vacation from Jan 15-20, Doctor appointment Jan 10 09:00-11:00

3. **Edit Role Qualifications:**
   - Click **"Edit Roles"** to modify which roles a worker can do
   - Only assign roles they're trained for

### 4. **Worker Difficulty Ratings** (Critical for Fairness!)

This is what makes the scheduling truly fair:

#### Export Rating Template
1. Go to period's **"Job Roles"** page
2. In the **"Worker Rating System"** card, click **"Export Rating Template"**
3. Download the CSV file (matrix format: workers × roles)

#### Fill Out Ratings
The CSV looks like this:
```
Worker Name    | Cook | Server | Manager | Cleaner
---------------|------|--------|---------|--------
Alice          | 3    | 4      | N/A     | 2
Bob            | 4    |        | 5       | 3
Carol          | 2    | 5      |         | 4
```

**Rating Scale:**
- **1:** Very Easy / Regular
- **2:** Light
- **3:** Moderate
- **4:** Hard
- **5:** Very Hard

**Instructions:**
- Each worker fills out ONE ROW
- Rate only roles they're qualified for
- Leave empty or write "N/A" for roles they can't/won't rate
- Be honest! The system detects gaming (all 1s or all 5s)

#### Import Ratings
1. Save the completed CSV
2. Click **"Import Worker Ratings"**
3. Upload the CSV file
4. Review the import results showing:
   - Average difficulty for each role
   - Number of workers who rated it
   - Warnings about extreme patterns

**Important:** The algorithm now uses INDIVIDUAL ratings, not just averages. This means:
- Alice might find "Cook" moderate (3.0) while Bob finds it hard (4.0)
- The algorithm assigns Alice more Cook shifts than Bob (fair to both!)

### 5. **Generate Schedule**

1. On the **"Job Roles"** page, ensure:
   - ✅ Job roles are defined
   - ✅ Workers exist and have qualifications
   - ✅ (Optional) Workers have submitted ratings

2. Click **"Generate Slots & Assign Workers"**

3. **Optional:** Enter a **Random Seed** for reproducibility
   - Same seed = identical results
   - Leave empty for variety

4. The algorithm will:
   - Create shift slots for all roles across the period
   - Assign workers fairly based on:
     - Qualifications
     - Availability
     - Individual difficulty ratings
     - Current workload balance

5. Review results:
   - Green = success
   - Yellow = some shifts unassigned (add more workers or adjust constraints)
   - Red = critical error (check logs)

### 6. **View and Verify Schedule**

#### Dashboard View
- Navigate to **"Home/Dashboard"**
- See complete schedule in table format:
  - Role & Instance
  - Start/End times
  - Duration
  - Assigned worker

#### Statistics View
- Navigate to **"Fairness Statistics"**
- See comprehensive analytics:
  - **Overall Period Statistics:** Total/assigned/unassigned shifts
  - **Fairness Metrics:**
    - Proportional Share: Workers getting ≥ their fair share
    - Envy-Free: Workers who don't prefer others' bundles
  - **Charts:**
    - Night shifts per worker
    - Weekend shifts distribution
    - Difficulty distribution
    - Role distribution per worker

#### Algorithm Logs
- Click **"Algorithm Logs"** button
- View step-by-step execution:
  - Which workers were considered for each shift
  - Why workers were rejected (not qualified, overlap, etc.)
  - Who was assigned and why
  - Final worker states

### 7. **Manual Adjustments**

If needed, you can manually edit assignments:

1. On the Dashboard, click **"Edit"** next to any shift
2. Select a different worker from dropdown
3. System warns if:
   - Worker not qualified
   - Time overlap detected
   - Would exceed max hours

### 8. **Export Schedule**

Export for distribution or record-keeping:

1. **CSV Export:** Simple text format
   - Click **"Export CSV"**
   - Opens in Excel, Google Sheets, etc.

2. **Excel Export:** Formatted spreadsheet
   - Click **"Export Excel"**
   - Professional formatting with:
     - Color-coded headers
     - Highlighted unassigned shifts
     - Auto-sized columns

---

## 📊 Understanding Fairness Metrics

The application uses concepts from **algorithmic economics** to measure fairness:

### Proportional Share
- **Definition:** Each worker gets at least 1/n of the total workload (in their own perception)
- **Example:** With 4 workers and 100 weighted hours total, each should get ≥25 weighted hours
- **Why it matters:** Ensures no one is drastically overworked

### Envy-Free (EF)
- **Definition:** No worker prefers another worker's complete assignment bundle
- **Example:** Alice with 30 weighted hours doesn't think Bob's 32 weighted hours is better
- **Why it matters:** Perfect fairness from everyone's perspective (rare to achieve!)

---

## 🛠️ Technology Stack

**Backend:**
- Python 3.8+
- Flask (web framework)
- SQLAlchemy (ORM)
- SQLite (database)

**Frontend:**
- Bootstrap 4 (UI framework)
- Chart.js (data visualization)
- Litepicker (date picker)
- Vanilla JavaScript

**Data Processing:**
- Pandas (CSV/Excel handling)
- OpenPyXL (Excel export)
- python-dateutil (date parsing)

---

## 🐛 Troubleshooting

### "No workers available to assign shifts"
- **Solution:** Add workers in "Manage Workers" and set their qualifications

### "Could not assign worker to shift X"
- **Possible reasons:**
  1. No workers qualified for that role → Add qualifications
  2. All qualified workers unavailable → Check constraints
  3. All qualified workers at max hours → Increase max hours or add workers
  4. Time restrictions conflict → Review role working hours

### Shifts remain unassigned
- Check **Algorithm Logs** for detailed rejection reasons
- Review **Fairness Statistics** to see worker workload
- Ensure workers are qualified for all roles
- Check for overly restrictive constraints

### Import ratings fails
- Ensure CSV format matches exported template (workers as rows, roles as columns)
- Use integers 1-5 only (no decimals, letters, or special characters)
- Leave cells empty or "N/A" for unrated roles
- Check for extreme patterns (all 1s or all 5s) - system will warn you

### Database errors
- Delete `app.db` and run `flask db upgrade` to recreate
- Check for migration issues with `flask db history`

---

## 📸 Screenshots Recommendation

*For visual learners, consider adding screenshots showing:*

1. **Dashboard** - Full schedule table with worker assignments
2. **Worker Management** - Adding worker with qualifications
3. **Job Roles** - Defining a role with time restrictions
4. **Rating Template** - CSV matrix format example
5. **Fairness Statistics** - Charts and metrics dashboard
6. **Algorithm Logs** - Step-by-step execution view
7. **Constraint Modal** - Adding vacation/appointment

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request


---

## 🙏 Acknowledgments

- Algorithmic fairness concepts inspired by research in fair division
- Built as part of an Algorithmic Economics course project
- Special thanks to the open-source community for Flask, SQLAlchemy, and Chart.js

---

## 📚 Further Reading

**Fair Division:**
- "Cake Cutting Algorithms" - Robertson & Webb
- "Fair Division and Collective Welfare" - Moulin
- [Envy-free item allocation](https://en.wikipedia.org/wiki/Envy-free_item_allocation)

---

**Happy Scheduling! 📅**
