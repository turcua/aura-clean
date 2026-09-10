"""
Aura Financial Tracker - Secure Version
Savings Goal Model
Sprint 13: Transfers + Budgets + Savings Goals

Security properties (contrast with vulnerable-version/models/savings_goal.py):
- All queries parameterized
- Ownership enforced in the SQL WHERE clause (id = %s AND user_id = %s)
- account_id validated by the caller (routes/api/savings_goals.py) as owned
  by the same user before being attached
- No mass assignment — user_id never accepted as a parameter to any method
- update() and add_progress() auto-promote status to 'achieved' once
  current_amount >= target_amount — fixes a real bug (BUG-008 in the
  vulnerable version), not just a security issue
"""


class SavingsGoal:
    def __init__(self, id=None, user_id=None, account_id=None, name=None,
                 target_amount=None, current_amount=None, target_date=None,
                 monthly_target=None, status=None, created_at=None):
        self.id = id
        self.user_id = user_id
        self.account_id = account_id
        self.name = name
        self.target_amount = target_amount
        self.current_amount = current_amount
        self.target_date = target_date
        self.monthly_target = monthly_target
        self.status = status
        self.created_at = created_at

    @property
    def progress_percent(self):
        if self.target_amount and self.target_amount > 0:
            return min(round((self.current_amount / self.target_amount) * 100, 1), 100)
        return 0

    @property
    def remaining_amount(self):
        return max(self.target_amount - self.current_amount, 0)

    @staticmethod
    def create(mysql, user_id, account_id, name, target_amount, current_amount, target_date, monthly_target):
        try:
            cursor = mysql.connection.cursor()
            status = 'achieved' if current_amount >= target_amount else 'active'
            cursor.execute(
                "INSERT INTO savings_goals (user_id, account_id, name, target_amount, current_amount, target_date, monthly_target, status) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (user_id, account_id, name, target_amount, current_amount, target_date, monthly_target, status)
            )
            mysql.connection.commit()
            goal_id = cursor.lastrowid
            cursor.close()
            return True, "Savings goal created successfully", goal_id
        except Exception as e:
            mysql.connection.rollback()
            if 'chk_goal_target_positive' in str(e):
                return False, "target_amount must be positive", None
            return False, "Could not create savings goal", None

    @staticmethod
    def get_by_id(mysql, goal_id, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, account_id, name, target_amount, current_amount, target_date, monthly_target, status, created_at "
                "FROM savings_goals WHERE id = %s AND user_id = %s",
                (goal_id, user_id)
            )
            row = cursor.fetchone()
            cursor.close()
            return SavingsGoal._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def get_all_by_user(mysql, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                "SELECT id, user_id, account_id, name, target_amount, current_amount, target_date, monthly_target, status, created_at "
                "FROM savings_goals WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,)
            )
            rows = cursor.fetchall()
            cursor.close()
            return [SavingsGoal._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def update(mysql, goal_id, user_id, account_id, name, target_amount, current_amount,
               target_date, monthly_target, status):
        try:
            if current_amount >= target_amount and status == 'active':
                status = 'achieved'
            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE savings_goals SET account_id = %s, name = %s, target_amount = %s, current_amount = %s, "
                "target_date = %s, monthly_target = %s, status = %s WHERE id = %s AND user_id = %s",
                (account_id, name, target_amount, current_amount, target_date, monthly_target, status, goal_id, user_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Savings goal not found or you don't have permission to edit it"
            return True, "Savings goal updated successfully"
        except Exception as e:
            mysql.connection.rollback()
            if 'chk_goal_target_positive' in str(e):
                return False, "target_amount must be positive"
            return False, "Could not update savings goal"

    @staticmethod
    def add_progress(mysql, goal_id, user_id, amount):
        try:
            goal = SavingsGoal.get_by_id(mysql, goal_id, user_id)
            if not goal:
                return False, "Savings goal not found or you don't have permission to update it"

            new_amount = goal.current_amount + amount
            new_status = goal.status
            if new_amount >= goal.target_amount and goal.status == 'active':
                new_status = 'achieved'

            cursor = mysql.connection.cursor()
            cursor.execute(
                "UPDATE savings_goals SET current_amount = %s, status = %s WHERE id = %s AND user_id = %s",
                (new_amount, new_status, goal_id, user_id)
            )
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Savings goal not found or you don't have permission to update it"
            return True, "Progress updated"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not update progress"

    @staticmethod
    def delete(mysql, goal_id, user_id):
        try:
            cursor = mysql.connection.cursor()
            cursor.execute("DELETE FROM savings_goals WHERE id = %s AND user_id = %s", (goal_id, user_id))
            mysql.connection.commit()
            affected = cursor.rowcount
            cursor.close()
            if affected == 0:
                return False, "Savings goal not found or you don't have permission to delete it"
            return True, "Savings goal deleted successfully"
        except Exception:
            mysql.connection.rollback()
            return False, "Could not delete savings goal"

    @staticmethod
    def _from_row(row):
        return SavingsGoal(
            id=row[0],
            user_id=row[1],
            account_id=row[2],
            name=row[3],
            target_amount=float(row[4]) if row[4] is not None else 0.0,
            current_amount=float(row[5]) if row[5] is not None else 0.0,
            target_date=row[6],
            monthly_target=float(row[7]) if row[7] is not None else None,
            status=row[8],
            created_at=row[9],
        )
