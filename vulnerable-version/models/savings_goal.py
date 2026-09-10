"""
Aura Financial Tracker - Vulnerable Version
Savings Goal Model (WITH INTENTIONAL VULNERABILITIES)
Sprint 4: Shadow Extractor
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
    def create(mysql, user_id, account_id, name, target_amount, current_amount,
               target_date, monthly_target):
        """
        VULNERABILITY: SQL Injection
        VULNERABILITY: Mass assignment (user_id from request)
        VULNERABILITY: No validation on amounts or dates
        VULNERABILITY: account_id can reference any user's account (IDOR)
        """
        try:
            cursor = mysql.connection.cursor()
            acc = account_id if account_id else 'NULL'
            td = f"'{target_date}'" if target_date else 'NULL'
            mt = monthly_target if monthly_target else 'NULL'
            curr = current_amount if current_amount else 0

            # VULN: SQL Injection
            cursor.execute(f"""
                INSERT INTO savings_goals
                    (user_id, account_id, name, target_amount, current_amount, target_date, monthly_target, status)
                VALUES
                    ({user_id}, {acc}, '{name}', {target_amount}, {curr}, {td}, {mt}, 'active')
            """)
            mysql.connection.commit()
            goal_id = cursor.lastrowid
            cursor.close()
            return True, "Savings goal created successfully", goal_id
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}", None

    @staticmethod
    def get_by_id(mysql, goal_id):
        """VULNERABILITY: SQL Injection, IDOR"""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(f"SELECT * FROM savings_goals WHERE id = {goal_id}")
            row = cursor.fetchone()
            cursor.close()
            return SavingsGoal._from_row(row) if row else None
        except Exception:
            return None

    @staticmethod
    def get_all_by_user(mysql, user_id):
        """VULNERABILITY: SQL Injection"""
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection
            cursor.execute(
                f"SELECT * FROM savings_goals WHERE user_id = {user_id} ORDER BY created_at DESC"
            )
            rows = cursor.fetchall()
            cursor.close()
            return [SavingsGoal._from_row(r) for r in rows]
        except Exception:
            return []

    @staticmethod
    def update(mysql, goal_id, user_id, account_id, name, target_amount,
               current_amount, target_date, monthly_target, status):
        """
        VULNERABILITY: SQL Injection, IDOR, Mass assignment
        VULNERABILITY: BUG-008 source - status not auto-set to 'achieved' even if current >= target
        """
        try:
            cursor = mysql.connection.cursor()
            acc = account_id if account_id else 'NULL'
            td = f"'{target_date}'" if target_date else 'NULL'
            mt = monthly_target if monthly_target else 'NULL'

            # VULN: SQL Injection, no ownership check, status not auto-computed
            cursor.execute(f"""
                UPDATE savings_goals
                SET user_id = {user_id}, account_id = {acc}, name = '{name}',
                    target_amount = {target_amount}, current_amount = {current_amount},
                    target_date = {td}, monthly_target = {mt}, status = '{status}'
                WHERE id = {goal_id}
            """)
            mysql.connection.commit()
            cursor.close()
            return True, "Savings goal updated successfully"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def add_progress(mysql, goal_id, amount):
        """
        Add amount to current_amount.
        VULNERABILITY: SQL Injection, IDOR
        VULNERABILITY: BUG-008 - does NOT auto-update status to 'achieved'
        """
        try:
            cursor = mysql.connection.cursor()
            # VULN: SQL Injection, status not updated even when target reached (BUG-008)
            cursor.execute(f"""
                UPDATE savings_goals
                SET current_amount = current_amount + {amount}
                WHERE id = {goal_id}
            """)
            mysql.connection.commit()
            cursor.close()
            return True, "Progress updated"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

    @staticmethod
    def delete(mysql, goal_id):
        """VULNERABILITY: SQL Injection, IDOR"""
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(f"DELETE FROM savings_goals WHERE id = {goal_id}")
            mysql.connection.commit()
            cursor.close()
            return True, "Savings goal deleted successfully"
        except Exception as e:
            mysql.connection.rollback()
            return False, f"Database error: {str(e)}"

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
            created_at=row[9]
        )
