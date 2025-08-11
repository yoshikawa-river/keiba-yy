from typing import Any, Dict, List, Optional

"""
JRA-VANデータリポジトリ

JRA-VANテーブルへのアクセスを管理するリポジトリクラス
"""

from datetime import date, datetime, timedelta

from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from src.data.converters.data_converter import DataConverter, RaceKey
from src.data.models.jravan_models import NChokyo, NKisyu, NRace, NUma, NUmaRace


class RaceRepository:
    """N_RACEテーブルのリポジトリ"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def get_by_key(self, race_key: RaceKey) -> Optional[NRace]:
        """複合キーでレースを取得"""
        return self.db.query(NRace).filter_by(**race_key.to_dict()).first()

    def get_by_race_id(self, race_id: str) -> Optional[NRace]:
        """レースIDでレースを取得"""
        race_key = RaceKey.from_race_id(race_id)
        return self.get_by_key(race_key)

    def get_by_date_range(
        self,
        start_date: date,
        end_date: date,
        jyo_cd: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> List[NRace]:
        """
        日付範囲でレースを取得

        Args:
            start_date: 開始日
            end_date: 終了日
            jyo_cd: 競馬場コード（オプション）
            limit: 取得件数制限
        """
        start_str = start_date.strftime("%Y")
        end_str = end_date.strftime("%Y")
        start_md = start_date.strftime("%m%d")
        end_md = end_date.strftime("%m%d")

        query = self.db.query(NRace)

        # 年またぎの考慮
        if start_date.year == end_date.year:
            # 同じ年の場合
            query = query.filter(
                and_(
                    NRace.Year == start_str,
                    NRace.MonthDay >= start_md,
                    NRace.MonthDay <= end_md,
                )
            )
        else:
            # 年をまたぐ場合
            query = query.filter(
                or_(
                    and_(NRace.Year == start_str, NRace.MonthDay >= start_md),
                    and_(NRace.Year == end_str, NRace.MonthDay <= end_md),
                    and_(NRace.Year > start_str, NRace.Year < end_str),
                )
            )

        if jyo_cd:
            query = query.filter(NRace.JyoCD == jyo_cd)

        query = query.order_by(NRace.Year, NRace.MonthDay, NRace.RaceNum)

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_by_jyo(
        self, jyo_cd: str, year: Optional[str] = None, limit: Optional[int] = None
    ) -> List[NRace]:
        """競馬場でレースを取得"""
        query = self.db.query(NRace).filter(NRace.JyoCD == jyo_cd)

        if year:
            query = query.filter(NRace.Year == year)

        query = query.order_by(NRace.Year.desc(), NRace.MonthDay.desc(), NRace.RaceNum)

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_grade_races(
        self, grade_cd: str, year: Optional[str] = None, limit: Optional[int] = None
    ) -> List[NRace]:
        """グレードレースを取得"""
        query = self.db.query(NRace).filter(NRace.GradeCD == grade_cd)

        if year:
            query = query.filter(NRace.Year == year)

        query = query.order_by(NRace.Year.desc(), NRace.MonthDay.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_recent_races(self, days: int = 7, jyo_cd: Optional[str] = None) -> list[NRace]:
        """最近のレースを取得"""
        end_date = datetime.now().date()
        start_date = end_date - timedelta(days=days)

        return self.get_by_date_range(start_date, end_date, jyo_cd)

    def count_by_year(self, year: str) -> int:
        """年ごとのレース数を取得"""
        return self.db.query(func.count(NRace.Year)).filter(NRace.Year == year).scalar()

    def get_race_with_entries(self, race_key: RaceKey) -> Optional[Dict[str, Any]]:
        """レースと出走情報を同時に取得"""
        race = self.get_by_key(race_key)
        if not race:
            return None

        # 出走情報を取得
        entries = (
            self.db.query(NUmaRace)
            .filter_by(**race_key.to_dict())
            .order_by(NUmaRace.Umaban)
            .all()
        )

        return {
            "race": DataConverter.nrace_to_dict(race),
            "entries": [DataConverter.numarace_to_dict(e) for e in entries],
        }

    def exists(self, race_key: RaceKey) -> bool:
        """レースが存在するか確認"""
        return self.db.query(NRace).filter_by(**race_key.to_dict()).count() > 0


class UmaRaceRepository:
    """N_UMA_RACEテーブルのリポジトリ"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def get_race_entries(
        self, race_key: RaceKey, include_canceled: bool = False
    ) -> List[NUmaRace]:
        """
        レースの出走馬を取得

        Args:
            race_key: レースキー
            include_canceled: 取消・除外馬を含むか
        """
        query = self.db.query(NUmaRace).filter_by(**race_key.to_dict())

        if not include_canceled:
            # 正常に出走した馬のみ（取消・除外を除く）
            query = query.filter(or_(NUmaRace.IJyoCD == "0", NUmaRace.IJyoCD is None))

        return query.order_by(NUmaRace.Umaban).all()

    def get_horse_history(
        self, ketto_num: str, before_date: Optional[date] = None, limit: int = 10
    ) -> List[NUmaRace]:
        """
        馬の過去レース履歴を取得

        Args:
            ketto_num: 血統登録番号
            before_date: この日付より前のレースを取得
            limit: 取得件数
        """
        query = self.db.query(NUmaRace).filter(NUmaRace.KettoNum == ketto_num)

        if before_date:
            before_str = before_date.strftime("%Y%m%d")
            year = before_str[:4]
            month_day = before_str[4:]

            query = query.filter(
                or_(
                    NUmaRace.Year < year,
                    and_(NUmaRace.Year == year, NUmaRace.MonthDay < month_day),
                )
            )

        return (
            query.order_by(NUmaRace.Year.desc(), NUmaRace.MonthDay.desc())
            .limit(limit)
            .all()
        )

    def get_jockey_results(
        self, kisyu_code: str, year: Optional[str] = None, limit: Optional[int] = None
    ) -> List[NUmaRace]:
        """騎手の成績を取得"""
        query = self.db.query(NUmaRace).filter(NUmaRace.KisyuCode == kisyu_code)

        if year:
            query = query.filter(NUmaRace.Year == year)

        query = query.order_by(NUmaRace.Year.desc(), NUmaRace.MonthDay.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_trainer_results(
        self, chokyo_code: str, year: Optional[str] = None, limit: Optional[int] = None
    ) -> List[NUmaRace]:
        """調教師の成績を取得"""
        query = self.db.query(NUmaRace).filter(NUmaRace.ChokyosiCode == chokyo_code)

        if year:
            query = query.filter(NUmaRace.Year == year)

        query = query.order_by(NUmaRace.Year.desc(), NUmaRace.MonthDay.desc())

        if limit:
            query = query.limit(limit)

        return query.all()

    def get_horse_vs_jockey(self, ketto_num: str, kisyu_code: str) -> List[NUmaRace]:
        """馬と騎手の組み合わせ成績を取得"""
        return (
            self.db.query(NUmaRace)
            .filter(
                and_(NUmaRace.KettoNum == ketto_num, NUmaRace.KisyuCode == kisyu_code)
            )
            .order_by(NUmaRace.Year.desc(), NUmaRace.MonthDay.desc())
            .all()
        )

    def calculate_win_rate(self, results: list[NUmaRace]) -> Dict[str, Any]:
        """
        成績から勝率等を計算

        Returns:
            win_rate: 勝率
            top3_rate: 複勝率
            avg_position: 平均着順
            total_races: 総レース数
        """
        if not results:
            return {
                "win_rate": 0.0,
                "top3_rate": 0.0,
                "avg_position": 0.0,
                "total_races": 0,
            }

        total = len(results)
        wins = 0
        top3 = 0
        positions = []

        for result in results:
            # 正常に完走した場合のみカウント
            if result.IJyoCD in ["0", None] and result.KakuteiJyuni:
                try:
                    position = int(result.KakuteiJyuni)
                    positions.append(position)
                    if position == 1:
                        wins += 1
                    if position <= 3:
                        top3 += 1
                except:
                    pass

        avg_position = sum(positions) / len(positions) if positions else 0

        return {
            "win_rate": wins / total,
            "top3_rate": top3 / total,
            "avg_position": avg_position,
            "total_races": total,
            "valid_races": len(positions),
        }


class UmaRepository:
    """N_UMAテーブルのリポジトリ"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def get_by_id(self, ketto_num: str) -> Optional[NUma]:
        """血統登録番号で馬を取得"""
        return self.db.query(NUma).filter(NUma.KettoNum == ketto_num).first()

    def get_by_name(self, name: str, exact: bool = True) -> list[NUma]:
        """馬名で馬を取得"""
        if exact:
            return self.db.query(NUma).filter(NUma.Bamei == name).all()
        return self.db.query(NUma).filter(NUma.Bamei.like(f"%{name}%")).all()

    def get_by_father(self, father_id: str) -> list[NUma]:
        """父馬で検索"""
        return (
            self.db.query(NUma).filter(NUma.Ketto3InfoHansyokuNum1 == father_id).all()
        )

    def get_by_mother_father(self, mother_father_id: str) -> list[NUma]:
        """母父で検索"""
        return (
            self.db.query(NUma)
            .filter(NUma.Ketto3InfoHansyokuNum5 == mother_father_id)
            .all()
        )

    def get_active_horses(self) -> list[NUma]:
        """現役馬を取得（削除されていない馬）"""
        return (
            self.db.query(NUma)
            .filter(or_(NUma.DelKubun == "0", NUma.DelKubun is None))
            .all()
        )

    def exists(self, ketto_num: str) -> bool:
        """馬が存在するか確認"""
        return self.db.query(NUma).filter(NUma.KettoNum == ketto_num).count() > 0


class KisyuRepository:
    """N_KISYUテーブルのリポジトリ"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def get_by_id(self, kisyu_code: str) -> Optional[NKisyu]:
        """騎手コードで騎手を取得"""
        return self.db.query(NKisyu).filter(NKisyu.KisyuCode == kisyu_code).first()

    def get_by_name(self, name: str, exact: bool = True) -> list[NKisyu]:
        """騎手名で騎手を取得"""
        if exact:
            return (
                self.db.query(NKisyu)
                .filter(or_(NKisyu.KisyuName == name, NKisyu.KisyuRyakusyo == name))
                .all()
            )
        return (
            self.db.query(NKisyu)
            .filter(
                or_(
                    NKisyu.KisyuName.like(f"%{name}%"),
                    NKisyu.KisyuRyakusyo.like(f"%{name}%"),
                )
            )
            .all()
        )

    def get_by_tozai(self, tozai_cd: str) -> list[NKisyu]:
        """東西所属で騎手を取得"""
        return self.db.query(NKisyu).filter(NKisyu.TozaiCD == tozai_cd).all()

    def get_active_jockeys(self) -> list[NKisyu]:
        """現役騎手を取得"""
        return (
            self.db.query(NKisyu)
            .filter(or_(NKisyu.DelKubun == "0", NKisyu.DelKubun is None))
            .all()
        )

    def exists(self, kisyu_code: str) -> bool:
        """騎手が存在するか確認"""
        return self.db.query(NKisyu).filter(NKisyu.KisyuCode == kisyu_code).count() > 0


class ChokyoRepository:
    """N_CHOKYOテーブルのリポジトリ"""

    def __init__(self, db_session: Session):
        self.db = db_session

    def get_by_id(self, chokyo_code: str) -> Optional[NChokyo]:
        """調教師コードで調教師を取得"""
        return (
            self.db.query(NChokyo).filter(NChokyo.ChokyosiCode == chokyo_code).first()
        )

    def get_by_name(self, name: str, exact: bool = True) -> list[NChokyo]:
        """調教師名で調教師を取得"""
        if exact:
            return (
                self.db.query(NChokyo)
                .filter(
                    or_(NChokyo.ChokyosiName == name, NChokyo.ChokyosiRyakusyo == name)
                )
                .all()
            )
        return (
            self.db.query(NChokyo)
            .filter(
                or_(
                    NChokyo.ChokyosiName.like(f"%{name}%"),
                    NChokyo.ChokyosiRyakusyo.like(f"%{name}%"),
                )
            )
            .all()
        )

    def get_by_tozai(self, tozai_cd: str) -> list[NChokyo]:
        """東西所属で調教師を取得"""
        return self.db.query(NChokyo).filter(NChokyo.TozaiCD == tozai_cd).all()

    def get_active_trainers(self) -> list[NChokyo]:
        """現役調教師を取得"""
        return (
            self.db.query(NChokyo)
            .filter(or_(NChokyo.DelKubun == "0", NChokyo.DelKubun is None))
            .all()
        )

    def exists(self, chokyo_code: str) -> bool:
        """調教師が存在するか確認"""
        return (
            self.db.query(NChokyo).filter(NChokyo.ChokyosiCode == chokyo_code).count()
            > 0
        )
