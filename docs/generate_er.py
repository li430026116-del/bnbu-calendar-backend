"""Generate updated ER diagram with relationship arrows using matplotlib.

Updated for the latest project structure:
- Teacher/Admin are separated at the portal/permission level, but admin is still stored
  through auth_user.role, so there is no standalone admin table.
- Added personal_tasks and assignment_submissions.
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch

# ── Table definitions ──────────────────────────────────────────────────────────
# Each table: list of (field_name, type_str, tag)  tag: PK / FK / UQ / IDX / ""
TABLES = {
    "auth_user": {
        "color": "#2C3E50", "label": "auth_user\n(User)",
        "fields": [
            ("id", "bigint", "PK"),
            ("username", "varchar(150)", "UQ"),
            ("password", "varchar(128)", ""),
            ("email", "varchar(254)", ""),
            ("role", "varchar(10)", "IDX"),
            ("avatar_url", "varchar(200)", ""),
            ("email_notifications", "bool", ""),
            ("dark_mode", "bool", ""),
            ("auto_sync", "bool", ""),
            ("is_active / is_staff", "bool", ""),
            ("date_joined", "datetime", ""),
        ],
    },
    "students": {
        "color": "#27AE60", "label": "students",
        "fields": [
            ("id", "bigint", "PK"),
            ("user_id", "bigint", "FK UQ"),
            ("student_id", "varchar(20)", "UQ"),
            ("name", "varchar(100)", ""),
            ("major_code", "varchar(10)", ""),
            ("major_name", "varchar(100)", ""),
            ("faculty", "varchar(10)", ""),
            ("grade", "int", ""),
            ("total_credit", "int", ""),
        ],
    },
    "teachers": {
        "color": "#27AE60", "label": "teachers",
        "fields": [
            ("id", "bigint", "PK"),
            ("user_id", "bigint", "FK UQ"),
            ("teacher_id", "varchar(20)", "UQ"),
            ("name", "varchar(100)", ""),
            ("faculty", "varchar(10)", ""),
            ("title", "varchar(50)", ""),
        ],
    },
    "semesters": {
        "color": "#8E44AD", "label": "semesters",
        "fields": [
            ("id", "bigint", "PK"),
            ("name", "varchar(50)", ""),
            ("start_date", "date", ""),
            ("end_date", "date", ""),
            ("is_current", "bool", ""),
        ],
    },
    "venues": {
        "color": "#E67E22", "label": "venues",
        "fields": [
            ("id", "bigint", "PK"),
            ("name", "varchar(50)", ""),
            ("building", "varchar(20)", ""),
            ("capacity", "int", ""),
            ("type", "varchar(20)", ""),
        ],
    },
    "categories": {
        "color": "#E67E22", "label": "categories",
        "fields": [
            ("id", "bigint", "PK"),
            ("name", "varchar(50)", ""),
            ("name_cn", "varchar(50)", ""),
            ("color", "varchar(10)", ""),
            ("icon", "varchar(30)", ""),
        ],
    },
    "courses": {
        "color": "#C0392B", "label": "courses",
        "fields": [
            ("id", "bigint", "PK"),
            ("code", "varchar(20)", "UQ"),
            ("name", "varchar(200)", ""),
            ("teacher_id", "bigint", "FK"),
            ("semester_id", "bigint", "FK"),
            ("venue_id", "bigint", "FK"),
            ("credit", "int", ""),
            ("schedule", "varchar(100)", ""),
            ("faculty", "varchar(10)", ""),
            ("max_students", "int", ""),
        ],
    },
    "assignments": {
        "color": "#C0392B", "label": "assignments",
        "fields": [
            ("id", "bigint", "PK"),
            ("course_id", "bigint", "FK IDX"),
            ("title", "varchar(200)", ""),
            ("description", "text", ""),
            ("deadline", "datetime", "IDX"),
            ("priority", "varchar(10)", ""),
            ("created_at", "datetime", ""),
            ("is_completed", "bool", ""),
        ],
    },
    "assignment_submissions": {
        "color": "#AF601A", "label": "assignment_submissions",
        "fields": [
            ("id", "bigint", "PK"),
            ("assignment_id", "bigint", "FK"),
            ("student_id", "bigint", "FK"),
            ("file", "varchar(255)", ""),
            ("submitted_at", "datetime", ""),
        ],
    },
    "enrollments": {
        "color": "#16A085", "label": "enrollments",
        "fields": [
            ("id", "bigint", "PK"),
            ("student_id", "bigint", "FK IDX"),
            ("course_id", "bigint", "FK IDX"),
            ("enrolled_at", "datetime", ""),
            ("status", "varchar(10)", "IDX"),
        ],
    },
    "events": {
        "color": "#2980B9", "label": "events",
        "fields": [
            ("id", "bigint", "PK"),
            ("title", "varchar(200)", ""),
            ("description", "text", ""),
            ("start_time", "datetime", "IDX"),
            ("end_time", "datetime", "IDX"),
            ("venue_id", "bigint", "FK"),
            ("category_id", "bigint", "FK IDX"),
            ("organizer", "varchar(100)", ""),
            ("is_public", "bool", ""),
            ("image", "varchar(255)", ""),
            ("created_by_id", "bigint", "FK"),
        ],
    },
    "notifications": {
        "color": "#7F8C8D", "label": "notifications",
        "fields": [
            ("id", "bigint", "PK"),
            ("user_id", "bigint", "FK IDX"),
            ("title", "varchar(200)", ""),
            ("content", "text", ""),
            ("type", "varchar(20)", ""),
            ("related_id", "int", ""),
            ("is_read", "bool", "IDX"),
            ("created_at", "datetime", "IDX"),
        ],
    },
    "custom_tags": {
        "color": "#7F8C8D", "label": "custom_tags",
        "fields": [
            ("id", "bigint", "PK"),
            ("user_id", "bigint", "FK"),
            ("name", "varchar(50)", ""),
            ("color", "varchar(10)", ""),
        ],
    },
    "feedback": {
        "color": "#7F8C8D", "label": "feedback",
        "fields": [
            ("id", "bigint", "PK"),
            ("user_id", "bigint", "FK"),
            ("title", "varchar(200)", ""),
            ("content", "text", ""),
            ("status", "varchar(10)", ""),
            ("created_at", "datetime", ""),
        ],
    },
    "event_subscriptions": {
        "color": "#16A085", "label": "event_subscriptions",
        "fields": [
            ("id", "bigint", "PK"),
            ("user_id", "bigint", "FK"),
            ("event_id", "bigint", "FK"),
            ("subscribed_at", "datetime", ""),
        ],
    },
    "share_links": {
        "color": "#7F8C8D", "label": "share_links",
        "fields": [
            ("id", "bigint", "PK"),
            ("user_id", "bigint", "FK"),
            ("token", "varchar(8)", "UQ IDX"),
            ("created_at", "datetime", ""),
        ],
    },
    "personal_tasks": {
        "color": "#884EA0", "label": "personal_tasks",
        "fields": [
            ("id", "bigint", "PK"),
            ("owner_id", "bigint", "FK IDX"),
            ("title", "varchar(200)", ""),
            ("description", "text", ""),
            ("due_at", "datetime", "IDX"),
            ("priority", "varchar(10)", ""),
            ("is_completed", "bool", ""),
            ("share_token", "varchar(32)", "UQ IDX"),
            ("source_task_id", "bigint", "FK"),
            ("created_at", "datetime", ""),
            ("updated_at", "datetime", ""),
        ],
    },
}

# ── FK relationships (child_table, parent_table, label) ───────────────────────
RELATIONS = [
    ("students", "auth_user", "user_id"),
    ("teachers", "auth_user", "user_id"),
    ("courses", "teachers", "teacher_id"),
    ("courses", "semesters", "semester_id"),
    ("courses", "venues", "venue_id"),
    ("assignments", "courses", "course_id"),
    ("assignment_submissions", "assignments", "assignment_id"),
    ("assignment_submissions", "students", "student_id"),
    ("enrollments", "students", "student_id"),
    ("enrollments", "courses", "course_id"),
    ("events", "venues", "venue_id"),
    ("events", "categories", "category_id"),
    ("events", "auth_user", "created_by_id"),
    ("notifications", "auth_user", "user_id"),
    ("custom_tags", "auth_user", "user_id"),
    ("feedback", "auth_user", "user_id"),
    ("event_subscriptions", "auth_user", "user_id"),
    ("event_subscriptions", "events", "event_id"),
    ("share_links", "auth_user", "user_id"),
    ("personal_tasks", "auth_user", "owner_id"),
    ("personal_tasks", "personal_tasks", "source_task_id"),
]

# ── Grid layout (col, row) ────────────────────────────────────────────────────
GRID = {
    "semesters": (0, 0),
    "venues": (1, 0),
    "categories": (2, 0),
    "teachers": (3, 0),

    "students": (0, 1),
    "auth_user": (1, 1),
    "courses": (2, 1),
    "events": (3, 1),

    "enrollments": (0, 2),
    "personal_tasks": (1, 2),
    "assignments": (2, 2),
    "event_subscriptions": (3, 2),

    "notifications": (0, 3),
    "custom_tags": (1, 3),
    "feedback": (2, 3),
    "share_links": (3, 3),

    "assignment_submissions": (2, 4),
}

# ── Drawing constants ─────────────────────────────────────────────────────────
COL_W = 3.7
ROW_H = 4.15
TBL_W = 3.35
FIELD_H = 0.30
HDR_H = 0.48
PAD_Y = 0.14

MAX_COL = max(c for c, _ in GRID.values()) + 1
MAX_ROW = max(r for _, r in GRID.values()) + 1
FIG_W = MAX_COL * COL_W + 0.8
FIG_H = MAX_ROW * ROW_H + 0.8

fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=150)
ax.set_xlim(0, FIG_W)
ax.set_ylim(0, FIG_H)
ax.axis('off')
fig.patch.set_facecolor('#F0F2F5')


def box_geom(tname):
    col, row = GRID[tname]
    n = len(TABLES[tname]["fields"])
    h = HDR_H + PAD_Y + n * FIELD_H + PAD_Y
    x = col * COL_W + 0.4
    y = FIG_H - (row * ROW_H + 0.55 + h)
    return x, y, TBL_W, h


BOX = {t: box_geom(t) for t in TABLES}


def edge_point(tname, toward):
    x, y, w, h = BOX[tname]
    tx, ty, tw, th = BOX[toward]
    cx, cy = x + w / 2, y + h / 2
    tcx, tcy = tx + tw / 2, ty + th / 2
    dx, dy = tcx - cx, tcy - cy
    if abs(dx) >= abs(dy):
        return ((x + w, cy), 'right') if dx > 0 else ((x, cy), 'left')
    return ((cx, y + h), 'top') if dy > 0 else ((cx, y), 'bottom')


for tname, info in TABLES.items():
    x, y, w, h = BOX[tname]
    color = info["color"]
    fields = info["fields"]
    label = info["label"]

    ax.add_patch(FancyBboxPatch((x + 0.07, y - 0.07), w, h,
                                boxstyle="round,pad=0.04", linewidth=0,
                                facecolor='#AAAAAA', alpha=0.35, zorder=1))

    ax.add_patch(FancyBboxPatch((x, y), w, h,
                                boxstyle="round,pad=0.04", linewidth=1.0,
                                edgecolor='#555555', facecolor='white', zorder=2))

    ax.add_patch(FancyBboxPatch((x, y + h - HDR_H), w, HDR_H,
                                boxstyle="round,pad=0.04", linewidth=0,
                                facecolor=color, zorder=3))

    ax.text(x + w / 2, y + h - HDR_H / 2, label,
            ha='center', va='center', fontsize=7.0, fontweight='bold',
            color='white', zorder=4, linespacing=1.3)

    ax.plot([x + 0.04, x + w - 0.04], [y + h - HDR_H, y + h - HDR_H],
            color='#BBBBBB', lw=0.5, zorder=4)

    for i, (fname, ftype, tag) in enumerate(fields):
        fy = y + h - HDR_H - PAD_Y - (i + 0.5) * FIELD_H
        is_pk = "PK" in tag
        is_fk = "FK" in tag
        bg = '#FFF3CD' if is_pk else ('#E3F2FD' if is_fk else 'white')
        ax.add_patch(mpatches.Rectangle(
            (x + 0.03, fy - FIELD_H / 2 + 0.02), w - 0.06, FIELD_H - 0.04,
            facecolor=bg, edgecolor='none', zorder=3))

        prefix = "PK " if is_pk else ("FK " if is_fk else "    ")
        pfx_color = '#B7950B' if is_pk else ('#1565C0' if is_fk else '#999999')
        ax.text(x + 0.12, fy, prefix, ha='left', va='center',
                fontsize=5.5, color=pfx_color, fontweight='bold', zorder=5)
        ax.text(x + 0.38, fy, fname, ha='left', va='center',
                fontsize=6.0, color='#1A1A1A', zorder=5,
                fontweight='bold' if is_pk else 'normal')
        ax.text(x + w - 0.08, fy, ftype, ha='right', va='center',
                fontsize=5.2, color='#888888', style='italic', zorder=5)

        if i < len(fields) - 1:
            ax.plot([x + 0.05, x + w - 0.05],
                    [fy - FIELD_H / 2 + 0.02, fy - FIELD_H / 2 + 0.02],
                    color='#EEEEEE', lw=0.4, zorder=4)

ARROW_COLORS = [
    '#E74C3C', '#8E44AD', '#2980B9', '#27AE60', '#E67E22', '#16A085', '#C0392B',
    '#D35400', '#1ABC9C', '#2C3E50', '#F39C12', '#7D3C98', '#117A65', '#922B21',
    '#1F618D', '#196F3D', '#6E2F8F', '#7B241C', '#1A5276', '#7D6608', '#4A235A'
]

for idx, (child, parent, fk_label) in enumerate(RELATIONS):
    (px, py), _ = edge_point(parent, child)
    (cx, cy), _ = edge_point(child, parent)
    color = ARROW_COLORS[idx % len(ARROW_COLORS)]

    rad = 0.12 if child != parent else 0.35
    if child == parent:
        x, y, w, h = BOX[child]
        cx, cy = x + w, y + h * 0.25
        px, py = x + w * 0.8, y

    ax.annotate(
        "",
        xy=(px, py), xytext=(cx, cy),
        arrowprops=dict(
            arrowstyle="-|>",
            color=color,
            lw=1.2,
            connectionstyle=f"arc3,rad={rad}",
            mutation_scale=10,
        ),
        zorder=6,
    )

    mx, my = (px + cx) / 2, (py + cy) / 2
    ax.text(mx, my, fk_label, fontsize=4.5, color=color,
            ha='center', va='center', zorder=7,
            bbox=dict(boxstyle='round,pad=0.15', facecolor='white',
                      edgecolor=color, linewidth=0.6, alpha=0.85))

ax.text(FIG_W / 2, FIG_H - 0.18,
        "BNBU Calendar Database — Updated ER Diagram",
        ha='center', va='top', fontsize=10, fontweight='bold', color='#2C3E50')

legend_items = [
    mpatches.Patch(facecolor='#FFF3CD', edgecolor='#B7950B', label='Primary Key (PK)'),
    mpatches.Patch(facecolor='#E3F2FD', edgecolor='#1565C0', label='Foreign Key (FK)'),
    mpatches.Patch(facecolor='white', edgecolor='#555555',
                   label='Arrow: FK → PK  (child → parent)'),
]
ax.legend(handles=legend_items, loc='lower left', fontsize=6,
          framealpha=0.9, edgecolor='#AAAAAA', ncol=3,
          bbox_to_anchor=(0.01, 0.005))

plt.tight_layout(pad=0.3)
out = "/mnt/data/updated_generate_er_style.png"
plt.savefig(out, dpi=150, bbox_inches='tight', facecolor='#F0F2F5')
print(f"Saved → {out}")
