from typing import List, Tuple, Optional
import copy
from tkinter import messagebox

PIECE_VALUE = 1
KING_VALUE = 3

RED_PIECE_COLOR = "#FF0000"
WHITE_PIECE_COLOR = "#FFFFFF"

class BotPlayer:
    def __init__(self, game_instance=None):
        self.color = "RED"
        self.game = game_instance
        self.nodes_evaluated = 0
        # Добавляем максимальную глубину поиска
        self.max_depth = 3
        self.stalemate_warning_shown = False
        
    def get_move(self) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        if not self.game:
            return None
            
        all_moves = self._get_all_moves_for_color(self.color)
        
        if not all_moves:
            if self._is_stalemate():
                self._show_stalemate_warning()
            return None
        
        self.nodes_evaluated = 0
        self.stalemate_warning_shown = False

        best_score = -float('inf')
        best_move = None
        
        # Сортируем ходы: сначала взятия, потом обычные
        capture_moves = [m for m in all_moves if self._is_capture_move(m[0], m[1])]
        normal_moves = [m for m in all_moves if not self._is_capture_move(m[0], m[1])]
        sorted_moves = capture_moves + normal_moves
        
        for move in sorted_moves:
            new_board = self._simulate_move(move[0], move[1])
            if new_board is None:
                continue
                
            # Используем полную глубину поиска
            score = self._minimax(
                new_board,
                depth=self.max_depth - 1,
                alpha=-float('inf'),
                beta=float('inf'),
                maximizing=False
            )
            
            if best_move and self.game:
                future_board = self._simulate_move(best_move[0], best_move[1])
                opponent_color = "WHITE" if self.color == "RED" else "RED"
                if future_board and self._is_stalemate(future_board, opponent_color):
                    self._show_stalemate_warning()

            if score > best_score:
                best_score = score
                best_move = move
        
        print(f"Nodes evaluated: {self.nodes_evaluated}")
        return best_move

    def _is_stalemate(self, board=None, color=None) -> bool:
        """Проверяет, является ли позиция патовой."""
        if board is None:
            if not self.game:
                return False
            board = self.game.get_board_state()
            color = self.color
        
        if not board:
            return False
        
        # Проверяем, есть ли ходы у указанного цвета
        moves = self._get_all_moves_for_board(board, color)
        
        # Если нет ходов и у цвета еще есть шашки на доске, то это пат
        if not moves:
            target_color = RED_PIECE_COLOR if color == "RED" else WHITE_PIECE_COLOR
            
            for row in range(8):
                for col in range(8):
                    piece = board[row][col]
                    if piece and piece["color"] == target_color:
                        return True  # Есть шашки, но нет ходов - пат
    
        return False

    def _show_stalemate_warning(self):
        """Показывает предупреждение о патовой ситуации"""
        if not self.stalemate_warning_shown and self.game and hasattr(self.game, 'root'):
            self.stalemate_warning_shown = True
            # Показываем сообщение
            self.game.root.after(0, lambda: messagebox.showinfo(
                "Патовая ситуация", 
                "Бот считает, что ситуация патовая!"
            ))

    def _minimax(self, board, depth: int, alpha: float, beta: float, maximizing: bool) -> float:
        self.nodes_evaluated += 1
        
        # Терминальные условия
        if depth == 0:
            return self._evaluate_position(board)
        
        current_color = "RED" if maximizing else "WHITE"
        moves = self._get_all_moves_for_board(board, current_color)
        
        # Если нет ходов, текущий игрок проиграл
        if not moves:
            if maximizing:
                return -1000  # RED проиграл
            else:
                return 1000   # WHITE проиграл
        
        if maximizing:
            max_eval = -float('inf')
            # Сортируем ходы для лучшего отсечения
            capture_moves = [m for m in moves if self._is_capture_move(m[0], m[1])]
            normal_moves = [m for m in moves if not self._is_capture_move(m[0], m[1])]
            sorted_moves = capture_moves + normal_moves
            
            for move in sorted_moves:
                new_board = self._simulate_move_on_board(board, move[0], move[1])
                if new_board is None:
                    continue
                eval = self._minimax(new_board, depth - 1, alpha, beta, False)
                max_eval = max(max_eval, eval)
                alpha = max(alpha, eval)
                if beta <= alpha:
                    break  # beta отсечение
            return max_eval
        else:
            min_eval = float('inf')
            capture_moves = [m for m in moves if self._is_capture_move(m[0], m[1])]
            normal_moves = [m for m in moves if not self._is_capture_move(m[0], m[1])]
            sorted_moves = capture_moves + normal_moves
            
            for move in sorted_moves:
                new_board = self._simulate_move_on_board(board, move[0], move[1])
                if new_board is None:
                    continue
                eval = self._minimax(new_board, depth - 1, alpha, beta, True)
                min_eval = min(min_eval, eval)
                beta = min(beta, eval)
                if beta <= alpha:
                    break  # alpha отсечение
            return min_eval
    
    def _get_all_moves_for_color(self, color: str) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        if not self.game:
            return []
        
        board = self.game.get_board_state()
        if not board:
            return []
            
        return self._get_all_moves_for_board(board, color)
    
    def _get_all_moves_for_board(self, board, color: str) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        moves = []
        target_color = RED_PIECE_COLOR if color == "RED" else WHITE_PIECE_COLOR
        
        # Сначала ищем взятия
        capture_moves = []
        normal_moves = []
        
        for row in range(8):
            for col in range(8):
                piece = board[row][col]
                if piece and piece["color"] == target_color:
                    piece_moves = self._get_moves_for_piece(board, row, col)
                    for move in piece_moves:
                        if self._is_capture_move(move[0], move[1]):
                            capture_moves.append(move)
                        else:
                            normal_moves.append(move)
        
        # Обязательное взятие
        if capture_moves:
            return capture_moves
        return normal_moves
    
    def _get_moves_for_piece(self, board, row: int, col: int) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        piece = board[row][col]
        if not piece:
            return []
        
        moves = []
        color = piece["color"]
        is_king = piece["is_king"]
        
        if is_king:
            # Для дамки - все направления
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            for dr, dc in directions:
                self._add_king_moves(board, row, col, dr, dc, color, moves)
        else:
            # Для простой шашки
            if color == WHITE_PIECE_COLOR:
                # Белые
                move_dirs = [(-1, -1), (-1, 1)]
                capture_dirs = [(-2, -2), (-2, 2)]
            else:
                # Красные
                move_dirs = [(1, -1), (1, 1)]
                capture_dirs = [(2, -2), (2, 2)]
            
            # Проверяем взятия
            for dr, dc in capture_dirs:
                new_r, new_c = row + dr, col + dc
                mid_r, mid_c = row + dr//2, col + dc//2
                
                if 0 <= new_r < 8 and 0 <= new_c < 8:
                    if (board[mid_r][mid_c] and 
                        board[mid_r][mid_c]["color"] != color and 
                        not board[new_r][new_c]):
                        moves.append(((row, col), (new_r, new_c)))
            
            # Если нет взятий,то обычные ходы
            if not self._has_any_captures(board, color):
                for dr, dc in move_dirs:
                    new_r, new_c = row + dr, col + dc
                    if 0 <= new_r < 8 and 0 <= new_c < 8 and not board[new_r][new_c]:
                        moves.append(((row, col), (new_r, new_c)))
        
        return moves
    
    def _add_king_moves(self, board, row: int, col: int, dr: int, dc: int, 
                        color: str, moves: List) -> None:
        """Добавляет все возможные ходы дамки в заданном направлении"""
        # Обычные ходы
        curr_r, curr_c = row + dr, col + dc
        while 0 <= curr_r < 8 and 0 <= curr_c < 8 and not board[curr_r][curr_c]:
            moves.append(((row, col), (curr_r, curr_c)))
            curr_r += dr
            curr_c += dc
        
        # Взятия
        curr_r, curr_c = row + dr, col + dc
        found_opponent = False
        
        while 0 <= curr_r < 8 and 0 <= curr_c < 8:
            if board[curr_r][curr_c]:
                if board[curr_r][curr_c]["color"] != color and not found_opponent:
                    # Проверка на взятие
                    next_r, next_c = curr_r + dr, curr_c + dc
                    if 0 <= next_r < 8 and 0 <= next_c < 8 and not board[next_r][next_c]:
                        moves.append(((row, col), (next_r, next_c)))
                    break
                else:
                    break
            curr_r += dr
            curr_c += dc
    
    def _has_any_captures(self, board, color: str) -> bool:
        """Проверяет есть ли у цвета взятия"""
        target_color = RED_PIECE_COLOR if color == "RED" else WHITE_PIECE_COLOR
        
        for row in range(8):
            for col in range(8):
                piece = board[row][col]
                if piece and piece["color"] == target_color:
                    if self._has_capture_from_position(board, row, col):
                        return True
        return False
    
    def _has_capture_from_position(self, board, row: int, col: int) -> bool:
        piece = board[row][col]
        if not piece:
            return False
        
        color = piece["color"]
        is_king = piece["is_king"]
        
        if is_king:
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            for dr, dc in directions:
                if self._can_king_capture(board, row, col, dr, dc, color):
                    return True
        else:
            if color == WHITE_PIECE_COLOR:
                capture_dirs = [(-2, -2), (-2, 2)]
            else:
                capture_dirs = [(2, -2), (2, 2)]
            
            for dr, dc in capture_dirs:
                new_r, new_c = row + dr, col + dc
                mid_r, mid_c = row + dr//2, col + dc//2
                
                if 0 <= new_r < 8 and 0 <= new_c < 8:
                    if (board[mid_r][mid_c] and 
                        board[mid_r][mid_c]["color"] != color and 
                        not board[new_r][new_c]):
                        return True
        
        return False
    
    def _can_king_capture(self, board, row: int, col: int, dr: int, dc: int, color: str) -> bool:
        """Проверяет может ли дамка взять в заданном направлении"""
        curr_r, curr_c = row + dr, col + dc
        found_opponent = False
        
        while 0 <= curr_r < 8 and 0 <= curr_c < 8:
            if board[curr_r][curr_c]:
                if board[curr_r][curr_c]["color"] != color and not found_opponent:
                    next_r, next_c = curr_r + dr, curr_c + dc
                    if 0 <= next_r < 8 and 0 <= next_c < 8 and not board[next_r][next_c]:
                        return True
                    return False
                else:
                    return False
            curr_r += dr
            curr_c += dc
        
        return False
    
    def _is_capture_move(self, start: Tuple[int, int], end: Tuple[int, int]) -> bool:
        return abs(end[0] - start[0]) == 2 and abs(end[1] - start[1]) == 2
    
    def _simulate_move(self, start: Tuple[int, int], end: Tuple[int, int]):
        if not self.game:
            return None
        
        board = self.game.get_board_state()
        if not board:
            return None
            
        return self._simulate_move_on_board(board, start, end)
    
    def _simulate_move_on_board(self, board, start: Tuple[int, int], end: Tuple[int, int]):
        """Симулирует ход на доске"""
        # Глубокое копирование доски
        new_board = copy.deepcopy(board)
        
        start_r, start_c = start
        end_r, end_c = end
        
        # Перемещаем шашку
        new_board[end_r][end_c] = new_board[start_r][start_c]
        new_board[start_r][start_c] = None
        
        # Если это взятие, удаляем взятую шашку
        if self._is_capture_move(start, end):
            mid_r = (start_r + end_r) // 2
            mid_c = (start_c + end_c) // 2
            new_board[mid_r][mid_c] = None
        
        # Проверяем превращение в дамку
        piece = new_board[end_r][end_c]
        if piece and not piece["is_king"]:
            if (end_r == 0 and piece["color"] == WHITE_PIECE_COLOR) or \
               (end_r == 7 and piece["color"] == RED_PIECE_COLOR):
                piece["is_king"] = True
        
        return new_board
    
    def _evaluate_position(self, board) -> float:
        """Оценивает позицию на доске"""
        score = 0
        
        for row in range(8):
            for col in range(8):
                piece = board[row][col]
                if piece:
                    value = KING_VALUE if piece["is_king"] else PIECE_VALUE
                    
                    # Дополнительный бонус за позицию
                    if piece["color"] == RED_PIECE_COLOR:
                        score += value
                        # Бонус за продвижение вперед для красных
                        if not piece["is_king"]:
                            score += (row / 10)  # Чем ближе к 7 ряду, тем лучше
                    else:
                        score -= value
                        # Бонус за продвижение вперед для белых
                        if not piece["is_king"]:
                            score -= ((7 - row) / 10)  # Чем ближе к 0 ряду, тем лучше
        
        return score