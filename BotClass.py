from typing import List, Tuple, Optional
import copy
from tkinter import messagebox
import random
import json
import os
import numpy as np

PIECE_VALUE = 1
KING_VALUE = 3

RED_PIECE_COLOR = "#FF0000"
WHITE_PIECE_COLOR = "#FFFFFF"

class QLearningBot:
    def __init__(self, game_instance=None, epsilon=0.1, alpha=0.1, gamma=0.9):
        self.color = "RED"
        self.game = game_instance
        self.nodes_evaluated = 0
        
        # Параметры Q-learning
        self.epsilon = epsilon  # exploration rate
        self.alpha = alpha      # learning rate
        self.gamma = gamma      # discount factor
        
        # Q-таблица: ключ - hash состояния, значение - словарь {hash_хода: Q_value}
        self.q_table = {}
        
        # Файл для сохранения Q-таблицы
        self.q_table_file = "q_table.json"
        self.load_q_table()
        
        # Отслеживание последнего состояния и действия для обучения
        self.last_state = None
        self.last_action = None
        
        self.stalemate_warning_shown = False
        
    def save_q_table(self):
        """Сохраняет Q-таблицу в файл"""
        # Конвертируем tuple ключи в строки для JSON
        serializable_q_table = {}
        for state_hash, actions in self.q_table.items():
            serializable_q_table[state_hash] = {}
            for action_hash, q_value in actions.items():
                serializable_q_table[state_hash][action_hash] = q_value
        
        with open(self.q_table_file, 'w') as f:
            json.dump(serializable_q_table, f, indent=2)
    
    def load_q_table(self):
        """Загружает Q-таблицу из файла"""
        if os.path.exists(self.q_table_file):
            try:
                with open(self.q_table_file, 'r') as f:
                    serializable_q_table = json.load(f)
                
                # Восстанавливаем структуру
                for state_hash, actions in serializable_q_table.items():
                    self.q_table[state_hash] = {}
                    for action_hash, q_value in actions.items():
                        self.q_table[state_hash][action_hash] = q_value
            except:
                self.q_table = {}
    
    def get_state_hash(self, board) -> str:
        """Создает хеш состояния доски для Q-таблицы"""
        state_repr = []
        for row in range(8):
            for col in range(8):
                piece = board[row][col]
                if piece is None:
                    state_repr.append('0')
                elif piece["color"] == WHITE_PIECE_COLOR:
                    state_repr.append('W' + ('K' if piece["is_king"] else 'P'))
                else:
                    state_repr.append('R' + ('K' if piece["is_king"] else 'P'))
        return ''.join(state_repr)
    
    def get_action_hash(self, start: Tuple[int, int], end: Tuple[int, int]) -> str:
        """Создает хеш действия"""
        return f"{start[0]},{start[1]}->{end[0]},{end[1]}"
    
    def get_q_value(self, state_hash: str, action_hash: str) -> float:
        """Получает Q-значение для пары состояние-действие"""
        if state_hash not in self.q_table:
            self.q_table[state_hash] = {}
        if action_hash not in self.q_table[state_hash]:
            self.q_table[state_hash][action_hash] = 0.0
        return self.q_table[state_hash][action_hash]
    
    def set_q_value(self, state_hash: str, action_hash: str, value: float):
        """Устанавливает Q-значение для пары состояние-действие"""
        if state_hash not in self.q_table:
            self.q_table[state_hash] = {}
        self.q_table[state_hash][action_hash] = value
    
    def update_q_value(self, state_hash: str, action_hash: str, reward: float, next_state_hash: str):
        """Обновляет Q-значение по формуле Q-learning"""
        current_q = self.get_q_value(state_hash, action_hash)
        
        # Находим максимальное Q для следующего состояния
        max_next_q = 0.0
        if next_state_hash in self.q_table and self.q_table[next_state_hash]:
            max_next_q = max(self.q_table[next_state_hash].values())
        
        # Формула Q-learning: Q(s,a) = Q(s,a) + α * [r + γ * max Q(s',a') - Q(s,a)]
        new_q = current_q + self.alpha * (reward + self.gamma * max_next_q - current_q)
        self.set_q_value(state_hash, action_hash, new_q)
    
    def get_reward(self, board, move_made: bool, is_capture: bool, 
                   piece_captured: bool, became_king: bool) -> float:
        """Вычисляет награду за действие"""
        reward = 0.0
        
        # Базовая награда за ход
        if move_made:
            reward += 0.1
        
        # Награда за взятие шашки
        if is_capture:
            reward += 5.0
        
        # Награда за превращение в дамку
        if became_king:
            reward += 3.0
        
        # Штраф за потерю своих шашек (будет вычислено при сравнении)
        
        # Оцениваем позицию на доске
        board_score = self._evaluate_position(board)
        reward += board_score / 100.0  # Нормализуем
        
        return reward
    
    def _evaluate_position(self, board) -> float:
        """Оценивает позицию на доске с точки зрения RED (бота)"""
        score = 0.0
        
        for row in range(8):
            for col in range(8):
                piece = board[row][col]
                if piece:
                    value = KING_VALUE if piece["is_king"] else PIECE_VALUE
                    
                    if piece["color"] == RED_PIECE_COLOR:
                        score += value
                        # Бонус за продвижение вперед
                        if not piece["is_king"]:
                            score += (row / 10.0)
                        # Бонус за центральные клетки
                        if 2 <= col <= 5:
                            score += 0.2
                    else:  # Белые шашки (противник)
                        score -= value
                        if not piece["is_king"]:
                            score -= ((7 - row) / 10.0)
        
        return score
    
    def get_move(self) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        """Выбирает ход, используя epsilon-greedy стратегию"""
        if not self.game or (hasattr(self.game, 'game_ended') and self.game.game_ended):
            return None
        
        all_moves = self._get_all_moves_for_color(self.color)
        
        print(f"[DEBUG] all_moves count: {len(all_moves)}")
        
        if not all_moves:
            return None
        
        self.nodes_evaluated = 0
        
        # Получаем хеш текущего состояния
        board = self.game.get_board_state()
        state_hash = self.get_state_hash(board)
        
        # Сортируем ходы: сначала взятия (они обычно лучше)
        capture_moves = [m for m in all_moves if self._is_capture_move(m[0], m[1])]
        normal_moves = [m for m in all_moves if not self._is_capture_move(m[0], m[1])]
        sorted_moves = capture_moves + normal_moves
        
        # Epsilon-greedy выбор
        if random.random() < self.epsilon:
            # Исследование: выбираем случайный ход
            chosen_move = random.choice(sorted_moves) if sorted_moves else None
            print(f"[RL Bot] Exploration: random move")
        else:
            # Эксплуатация: выбираем лучший ход по Q-таблице
            best_move = None
            best_q = -float('inf')
            
            for move in sorted_moves:
                action_hash = self.get_action_hash(move[0], move[1])
                q_value = self.get_q_value(state_hash, action_hash)
                
                if q_value > best_q:
                    best_q = q_value
                    best_move = move
            
            chosen_move = best_move
            print(f"[RL Bot] Exploitation: best Q={best_q:.3f}")
        
        # Сохраняем состояние и действие для последующего обучения
        if chosen_move:
            self.last_state = state_hash
            self.last_action = self.get_action_hash(chosen_move[0], chosen_move[1])
        
        print(f"Q-table size: {len(self.q_table)} states")
        return chosen_move
    
    def learn_from_outcome(self, final_board, winner_color: str):
        """Обучение после завершения игры"""
        if hasattr(self, '_last_learned_outcome') and self._last_learned_outcome:
            return

        if self.last_state and self.last_action:
            # Финальная награда
            if winner_color == self.color:
                final_reward = 100.0  # Победа
            else:
                final_reward = -50.0  # Поражение
            
            # Обновляем Q-значение для последнего действия
            current_q = self.get_q_value(self.last_state, self.last_action)
            new_q = current_q + self.alpha * (final_reward - current_q)
            self.set_q_value(self.last_state, self.last_action, new_q)
            
            print(f"[RL Bot] Learned from outcome: reward={final_reward}")
            self.save_q_table()
    
    def learn_from_move(self, before_state_hash: str, action_hash: str, 
                        after_board, reward: float):
        """Обучение после каждого хода"""
        after_state_hash = self.get_state_hash(after_board)
        self.update_q_value(before_state_hash, action_hash, reward, after_state_hash)
    
    def _is_stalemate(self, board=None, color=None) -> bool:
        """Проверяет, является ли позиция патовой"""
        if board is None:
            if not self.game:
                return False
            board = self.game.get_board_state()
            color = self.color
        
        if not board:
            return False

        

        target_color = RED_PIECE_COLOR if color == "RED" else WHITE_PIECE_COLOR
            
        for row in range(8):
            for col in range(8):
                piece = board[row][col]
                if piece and piece["color"] == target_color:
                    moves = self._get_moves_for_piece(board, row, col)
                    if moves:
                        return False
        
        return True

    def _show_stalemate_warning(self):
        """Показывает предупреждение о патовой ситуации"""
        if not self.stalemate_warning_shown and self.game and hasattr(self.game, 'root'):
            self.stalemate_warning_shown = True
            self.game.root.after(0, lambda: messagebox.showinfo(
                "Патовая ситуация", 
                "Бот считает, что ситуация патовая!"
            ))
    
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
            directions = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
            for dr, dc in directions:
                self._add_king_moves(board, row, col, dr, dc, color, moves)
        else:
            if color == WHITE_PIECE_COLOR:
                move_dirs = [(-1, -1), (-1, 1)]
                capture_dirs = [(-2, -2), (-2, 2)]
            else:
                move_dirs = [(1, -1), (1, 1)]
                capture_dirs = [(2, -2), (2, 2)]
            
            has_captures_for_this_piece = False

            for dr, dc in capture_dirs:
                new_r, new_c = row + dr, col + dc
                mid_r, mid_c = row + dr//2, col + dc//2
                
                if 0 <= new_r < 8 and 0 <= new_c < 8:
                    if (board[mid_r][mid_c] and 
                        board[mid_r][mid_c]["color"] != color and 
                        not board[new_r][new_c]):
                        moves.append(((row, col), (new_r, new_c)))
                        has_captures_for_this_piece = True
            
            if not has_captures_for_this_piece:
                for dr, dc in move_dirs:
                    new_r, new_c = row + dr, col + dc
                    if 0 <= new_r < 8 and 0 <= new_c < 8 and not board[new_r][new_c]:
                        moves.append(((row, col), (new_r, new_c)))
        
        return moves
    
    def _add_king_moves(self, board, row: int, col: int, dr: int, dc: int, 
                        color: str, moves: List) -> None:
        curr_r, curr_c = row + dr, col + dc
        while 0 <= curr_r < 8 and 0 <= curr_c < 8 and not board[curr_r][curr_c]:
            moves.append(((row, col), (curr_r, curr_c)))
            curr_r += dr
            curr_c += dc
        
        curr_r, curr_c = row + dr, col + dc
        found_opponent = False
        
        while 0 <= curr_r < 8 and 0 <= curr_c < 8:
            if board[curr_r][curr_c]:
                if board[curr_r][curr_c]["color"] != color and not found_opponent:
                    next_r, next_c = curr_r + dr, curr_c + dc
                    if 0 <= next_r < 8 and 0 <= next_c < 8 and not board[next_r][next_c]:
                        moves.append(((row, col), (next_r, next_c)))
                    break
                else:
                    break
            curr_r += dr
            curr_c += dc
    
    def _has_any_captures(self, board, color: str) -> bool:
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
    
    def _simulate_move_on_board(self, board, start: Tuple[int, int], end: Tuple[int, int]):
        new_board = copy.deepcopy(board)
        
        start_r, start_c = start
        end_r, end_c = end
        
        new_board[end_r][end_c] = new_board[start_r][start_c]
        new_board[start_r][start_c] = None
        
        if self._is_capture_move(start, end):
            mid_r = (start_r + end_r) // 2
            mid_c = (start_c + end_c) // 2
            new_board[mid_r][mid_c] = None
        
        piece = new_board[end_r][end_c]
        if piece and not piece["is_king"]:
            if (end_r == 0 and piece["color"] == WHITE_PIECE_COLOR) or \
               (end_r == 7 and piece["color"] == RED_PIECE_COLOR):
                piece["is_king"] = True
        
        return new_board


# Для обратной совместимости сохраняем старое имя класса
BotPlayer = QLearningBot