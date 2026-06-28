from app.schemas.growth import MilestoneItem

_MILESTONES_RAW = [
    # 0-3 months
    {
        "age_months": 2,
        "title": "俯卧抬头",
        "description": "俯卧时能短暂抬头 45 度",
        "category": "motor",
    },
    {
        "age_months": 3,
        "title": "追视移动物体",
        "description": "眼睛能跟随 180 度移动的物体",
        "category": "cognitive",
    },
    # 4-6 months
    {
        "age_months": 4,
        "title": "翻身",
        "description": "能从俯卧翻到仰卧",
        "category": "motor",
    },
    {
        "age_months": 5,
        "title": "抓握物品",
        "description": "能主动伸手抓取眼前玩具",
        "category": "motor",
    },
    {
        "age_months": 6,
        "title": "独坐片刻",
        "description": "双手支撑下可独坐",
        "category": "motor",
    },
    {
        "age_months": 6,
        "title": "咿呀发声",
        "description": "能发出元音和辅音组合",
        "category": "language",
    },
    # 7-12 months
    {
        "age_months": 8,
        "title": "爬行",
        "description": "能腹部离地爬行",
        "category": "motor",
    },
    {
        "age_months": 9,
        "title": "扶站",
        "description": "能扶着家具站立",
        "category": "motor",
    },
    {
        "age_months": 10,
        "title": "挥手再见",
        "description": "能模仿挥手动作",
        "category": "social",
    },
    {
        "age_months": 12,
        "title": "独站",
        "description": "能独立站立数秒",
        "category": "motor",
    },
    {
        "age_months": 12,
        "title": "第一个词",
        "description": "能有意识地叫爸爸妈妈",
        "category": "language",
    },
    # 13-24 months
    {
        "age_months": 15,
        "title": "独走",
        "description": "能独立走几步",
        "category": "motor",
    },
    {
        "age_months": 18,
        "title": "模仿家务",
        "description": "能模仿简单家务动作",
        "category": "social",
    },
    {
        "age_months": 18,
        "title": "指认物品",
        "description": "能按名称指认常见物品",
        "category": "cognitive",
    },
    {
        "age_months": 24,
        "title": "两词句",
        "description": "能说两个词组成的短句",
        "category": "language",
    },
    # 25-36 months
    {
        "age_months": 30,
        "title": "上下楼梯",
        "description": "能扶着扶手上楼梯",
        "category": "motor",
    },
    {
        "age_months": 36,
        "title": "骑三轮车",
        "description": "能蹬三轮车前进",
        "category": "motor",
    },
    {
        "age_months": 36,
        "title": "说出姓名",
        "description": "能说出自己的名字和年龄",
        "category": "language",
    },
]


def get_all_milestones() -> list[MilestoneItem]:
    return [MilestoneItem(**m) for m in _MILESTONES_RAW]


def _milestone_status(age_months: int | None, expected_age_months: int) -> str:
    """Classify milestone status based on the child's actual age.

    Rules (assuming no explicit completion record):
    - delayed: 实际年龄已超过预期 2 个月以上，仍未达成
    - achieved: 实际年龄已达到或略超过预期（0-2 个月），视为已达成
    - warning: 实际年龄接近预期（还差 1 个月以内），需要关注
    - normal: 距离预期还有一段时间，正常等待
    """
    if age_months is None:
        return "normal"
    if age_months > expected_age_months + 2:
        return "delayed"
    if age_months >= expected_age_months:
        return "achieved"
    if age_months >= expected_age_months - 1:
        return "warning"
    return "normal"


def get_milestones_for_age(age_months: int | None) -> list[MilestoneItem]:
    milestones = get_all_milestones()
    result: list[MilestoneItem] = []
    for m in milestones:
        status = _milestone_status(age_months, m.age_months)
        result.append(
            MilestoneItem(
                age_months=m.age_months,
                title=m.title,
                description=m.description,
                category=m.category,
                is_completed=status == "achieved",
                status=status,
            )
        )
    return result


def get_milestone_categories() -> list[str]:
    return sorted({m.category for m in get_all_milestones()})
