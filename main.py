import re
from typing import Match, Union


class Declaration:
    def __init__(self, var_type, var_name, var_value=None):
        self.var_type = var_type.strip()
        self.var_name = var_name.strip()
        self.var_value = var_value
        if self.var_value is not None:
            self.var_value = self.var_value.strip()
    
    def __repr__(self):
        res = f"{self.var_type} {self.var_name}"
        if self.var_value is not None:
            res += f" = {self.var_value}"
        return res
    
    def reassign(self):
        return f"{self.var_name} = {self.var_value}"

class ParsedDeclaration:
    def __init__(self):
        self.decs = []

    def add_dec(self, dec):
        if type(dec) is list:
            for i in dec:
                self.decs.append(i)
        else:
            self.decs.append(dec)

    def get_dec(self):
        res = ""
        for i in self.decs:
            res += i.__repr__() + "; "
        return res

class scope_data:
    def __init__(self):
        self.variable_refs = {}
        self.sub_dict = {}
    
    def delete_dup_refs(self, other_sd_vars):
        res = {}
        for k, v in self.variable_refs.items():
            if k not in other_sd_vars:
                res[k] = v
        self.variable_refs = res
    
    def add_refs(self, ref_reset_dict={}):
        for k, v in ref_reset_dict.items():
            self.variable_refs[k] = v

    def add_subs(self, sub_dict={}):
        for k, v in sub_dict.items():
            self.sub_dict[k] = v

class lang_token:
    def __init__(self, token_type, start_idx, end_idx, routineable=True, actual_value=""):
        self.token_type = token_type
        self.start = start_idx
        self.end = end_idx
        self.routineable = routineable
        self.actual_value = actual_value
    
    def __repr__(self):
        return f"{self.token_type}: {self.start}-{self.end}"

    def actual_repr(self, txt):
        return f"{txt[self.start:self.end]}" if self.actual_value == "" else self.actual_value
        

class Interpreter:
    def __init__(self):
        self.variable_refs = []
        self.user_custom_variables = ParsedDeclaration()
        self.default_var_value = 0

        self.new_timer_id = 0
        self.new_var_id = 0
        self.new_iter_id = 0
        self.new_cond_id = 0
        self.new_routine_id = 0
        self.new_func_id = 0
        self.new_loop_var_id = 0
        self.new_str_swap_id = 0
        self.main_timer = "_mt0"
        self.NewVar = self.generate_variable()
        self.NewTimer = self.generate_variable(is_timer=True)
        self.NewCond = self.generate_variable(is_condition=True)
        self.NewIter = self.generate_variable(is_iterator=True)
        self.NewRoutine = self.generate_variable(is_routine=True)
        self.NewLoopVar = self.generate_variable(is_loop_var=True)
        self.NewFunc = self.generate_variable(is_func=True)
        self.NewStrSwap = self.generate_variable(is_str_swap=True)

        self.swp = "\"\"\"\'\'\'``````\'\'\'\"\"\""
        self.regex_if = "(if)( )*\(.*?\)( )*\{"
        self.regex_if_else = "((if)( )*\(.*?\)( )*\{)|((else)( )*\{)"
        self.regex_declaration_name_and_value = "[a-zA-Z_]([a-zA-Z0-9_])*?( )*=.+"
        self.regex_type_declarations = "(unsigned |signed |long |short |u|nu|s)?(byte|short|int|long|float|double|char)*?( )(_|[a-zA-Z]){1}([a-zA-Z0-9_])*(( )*=( )*[a-zA-Z0-9]+)?"
        self.regex_declare_start = "( )*?[a-zA-Z0-9]+?( )*\="
        self.regex_for_declare_type_start = "(sbyte|byte|short|ushort|int|uint|long|ulong|nint|nuint)( )*?"
        self.regex_for_declare_name_start = "( )*?.+?\="
        self.regex_for_declare_value_start = "\=.+"
        self.regex_line = "([^}]+?;)"
        self.regex_reset_every_loop_vars = "((_t)|(_c)|(_r)|(_v)|(_l))"
        self.regex_reserved_start = "((if|for|while|switch)( )*\(.*?\)( )*\{)|((else|thread)( )*\{)"
        self.regex_sleep = "(sleep)( )*?\(.+?\)"
        self.regex_setup = "(void setup)\(\)( )*\{"
        self.regex_loop = "(void loop)\(\)( )*\{"
        self.regex_thread = "thread( )*\{"

    def generate_variable(self, is_timer=False, is_condition=False, is_routine=False, is_func=False, is_iterator=False, is_loop_var=False, is_str_swap=False):
        while True:
            if is_timer:
                yield f"_t{self.new_timer_id}"
                self.new_timer_id += 1
            elif is_condition:
                yield f"_c{self.new_cond_id}"
                self.new_cond_id += 1
            elif is_routine:
                yield f"_r{self.new_routine_id}"
                self.new_routine_id += 1
            elif is_func:
                yield f"_f{self.new_func_id}"
                self.new_func_id += 1
            elif is_iterator:
                yield f"_i{self.new_iter_id}"
                self.new_iter_id += 1
            elif is_loop_var:
                yield f"_l{self.new_loop_var_id}"
                self.new_loop_var_id += 1
            elif is_str_swap:
                yield f"{self.new_str_swap_id}"
                self.new_str_swap_id += 1
            else:
                yield f"_v{self.new_var_id}"
                self.new_var_id += 1

    def declare(self, s, vartype="int", val="0") -> str:
        return f"{vartype} {s} = {val};"

    def sub_var(self, parent_str: str, old_str: str, new_str: str) -> str:
        return re.sub(f"(?<![a-zA-Z0-9_])({old_str})(?![a-zA-Z0-9_])", new_str, parent_str)

    def reset_vars(self, vars):
        if type(vars) is list:
            res_list = []
            vars.sort(key=lambda x: x[0:7])
            for v in vars:
                if re.match("_t", v.strip()) and re.search("_c", v.strip()) is None:
                    reset_str = f"{v.strip()} = {self.main_timer}; "
                else:
                    reset_str = f"{v.strip()} = 0; "
                res_list.append(reset_str)
            return "".join(res_list)
        elif type(vars) is dict:
            retlist = [f"{k} = {v}; " for k, v in vars.items()]
            retlist.sort(key=lambda x: x[0:7])
            return "".join(retlist)

    def parse_declaration(self, dec: str):
        """ the lengths i went just to avoid 5 minutes of regex in this function are record breaking """
        if "," not in dec:
            if "=" in dec:
                main_splt = dec.split("=")   # [before=, after=]
                splt1 = main_splt[0].split()
                return [Declaration(" ".join(splt1[:-1]), splt1[-1], main_splt[1])]
            else:
                main_splt = dec.split()
                return [Declaration(main_splt[:-1], main_splt[-1])]
        else:
            res = []
            if "=" not in dec:
                main_splt = dec.split(",")
                splt1 = main_splt[0].split()
                vars_declared = main_splt[1:]
                vars_declared.append(splt1[-1])
                for v in vars_declared:
                    res.append(Declaration(" ".join(splt1[:-1]), v))
                return res
            else:
                main_split = dec.split(",")
                splt1 = main_split[0].split("=")    # [before=, after=] :   ["unassigned int a", "9"]
                splt1_varname = splt1[0].split()[-1]
                vars_declared = main_split[1:]
                vars_declared.append(f"{splt1_varname} = {splt1[-1]}")
                for v in vars_declared:
                    vsplt = v.split("=")
                    vval = vsplt[-1]
                    vsplt0 = vsplt[0].split()
                    vname = vsplt0[-1]
                    vtype = " ".join(splt1[0].split()[:-1])
                    res.append(Declaration(vtype, vname, vval))
                return res

    def varname_from_dec(self, dec: str) -> str:
        splt = dec.split()
        if "=" in splt:
            return splt[-3]
        else:
            return splt[-1]

    def custom_var_declaration(self, user_vars: ParsedDeclaration) -> dict[str: str]:
        res = {}
        for uv in user_vars.decs:
            new_var = next(self.NewVar)
            res[uv.var_name] = new_var
        return res

    def match_brackets(self, s, only_first=False, get_index=False):
        # get_index only works for only_first for now
        brackets = []
        current_pos = [len(s), 0]
        current_count = 0
        for i in range(len(s)):
            match s[i]:
                case "{":
                    if current_count == 0:
                        current_pos[0] = i
                        current_count = 1
                    else:
                        current_count += 1
                case "}":
                    if current_count == 1:
                        current_pos[1] = i
                        current_count = 0
                        if get_index:
                            brackets.append((current_pos[0], current_pos[1]+1))
                        else:
                            brackets.append(s[current_pos[0]:current_pos[1]+1])
                        current_pos = [len(s), 0]
                        if only_first:
                            return brackets[0]
                    else:
                        current_count -= 1
        return brackets

    def get_inner_scope(self, scope: str, sd=scope_data) -> list[lang_token]:
        scopes = []

        reserved_starts = []
        reserved_starts_matches = re.finditer(self.regex_reserved_start, scope)
        reserved_scopes = self.match_brackets(scope, get_index=True)   # adds 1 to i.end()
        # pretty fucking gross ngl
        for b in reserved_starts_matches:
            for a in reserved_scopes:
                if abs(b.end() - a[0]) <= 1:        # if this is the '{' that ended the keyword
                    reserved_starts.append(b)
                    break
        
        for b, a in zip(reserved_starts, reserved_scopes):
            scopes.append(lang_token("parent", b.start(), a[1], routineable=False))

        regular_lines = re.finditer(self.regex_line, scope)
        for i in regular_lines:
            special = ""
            actual_value = ""
            lang_token_type = "child"
            is_routinable = True
            if not any(b.start < i.end() < b.end for b in scopes):
                token_val = scope[i.start():i.end()+1].strip()[:-1]
                if re.match(self.regex_sleep, token_val):
                    lang_token_type = "sleep"
                    is_routinable = False
                    # self.has_sleep = True
                elif re.match(self.regex_type_declarations, token_val):
                    parsed_dec = self.parse_declaration(token_val)
                    self.user_custom_variables.add_dec(parsed_dec)
                    rs = ""
                    for dc in parsed_dec:
                        if dc.var_value is not None: # if variable was declared with value
                            rs += dc.reassign() + "; "
                    if rs != "":
                        actual_value = rs
                    else:
                        actual_value = " "      # remove this line, because it doesnt assign a value, and we declare in user_custom_variables
                elif token_val == "continue":
                    is_routinable = False
                    lang_token_type = "blob"
                    actual_value = sd.sub_dict.get("continue", "")
                elif token_val == "break":
                    is_routinable = False
                    lang_token_type = "blob"
                    actual_value = sd.sub_dict.get("break", "")
                scopes.append(lang_token(lang_token_type, i.start(), i.end()+1, routineable=is_routinable, actual_value=actual_value))
        scopes.sort(key=lambda x: x.start)
        return scopes

    def routine_from_micro_scope(self, scope: list[lang_token]) -> list[list[lang_token]]:
        routines = []
        current_routine = []
        for s in scope:
            if s.routineable:
                current_routine.append(s)
            else:
                if len(current_routine) > 0:
                    routines.append(current_routine)
                    current_routine = []
                routines.append(s)
        if len(current_routine) > 0:
            routines.append(current_routine)
        return routines

    def group_routine(self, routine: list[lang_token], routine_var, parent_str="") -> str:
        if parent_str == "":
            parent_str = self.input_code
        routine_str = "".join([f"{i.actual_repr(parent_str)}" for i in routine])
        res = f"if ({routine_var} == 0) {{ {routine_str} {routine_var} = 1; }}"
        return res

    def scope_to_micro_scopes(self, cmds: list[str]) -> list[list[lang_token]]:
        # cmds = [*txt.split(";")]
        if "" in cmds:
            cmds.remove("")     # temp fix this shit
        cmds.reverse()      # iterating from end to start

        sleep_indexes = []
        for i in range(len(cmds)):
            if cmds[i].token_type == "sleep":
                sleep_indexes.append(i)
        if len(sleep_indexes) == 0:
            return [cmds[::-1]]
        sleep_indexes.sort()
        cmd_scopes = []
        for i in range(len(sleep_indexes)):
            start_idx = sleep_indexes[i-1]+1 if i != 0 else None
            end_idx = sleep_indexes[i]+1
            cmd_scopes.append(cmds[start_idx:end_idx][::-1])    # reversing back before handing to translation
        cmd_scopes.reverse()                                    # reversing the entire scope list because its also reversed
        if sleep_indexes[-1] < len(cmds) -1:
            initial_code = cmds[sleep_indexes[-1]+1:][::-1]     # reversing back same as above ^
            cmd_scopes.insert(0, initial_code)  # inserting it at position 0 becuase its the first :-)
        return cmd_scopes

    def translate_sleep(self, sleep_token: lang_token, content_str:str, parent_str="", sd=scope_data) -> tuple[str, str, str]:  
        declaration = ""

        sleep_timer = next(self.NewTimer)
        sleep_timer_checker = f"{sleep_timer}_c"
        sleep_timer_declare = self.declare(sleep_timer, vartype="unsigned long")
        sleep_timer_checker_declare = self.declare(sleep_timer_checker, vartype="unsigned char",val="0")
        sleep_timer_target = sleep_token.actual_repr(parent_str).replace(";", "").strip()[6:-1]
        timer_template = f"if ({sleep_timer_checker} == 0) {{ {sleep_timer} = {self.main_timer}; {sleep_timer_checker} = 1; }} if ({self.main_timer} - {sleep_timer} >= {sleep_timer_target}) {{ {content_str} }} else {{ return; }} "
        
        self.variable_refs.extend([sleep_timer, sleep_timer_checker])
        sd.add_refs(ref_reset_dict={sleep_timer: self.main_timer, sleep_timer_checker: self.default_var_value})
        declaration += sleep_timer_declare
        declaration += sleep_timer_checker_declare
        return sd, declaration, timer_template

    def translate_microscopes(self, mscp, parent_str="", sd=scope_data) -> tuple[str, str, str]:
        declaration = ""
        result = ""     # results in here well be appended side by side, not recursively.
        for s in mscp:
            sleep_token = None
            micro_result = ""
            routines = self.routine_from_micro_scope(s)
            for i in routines:
                if type(i) is not list:     # this is the one im looking for
                    if i.token_type == "parent":
                        new_par = i.actual_repr(parent_str)
                        new_sd, new_dec, new_tex = self.translate_reserved(new_par, sd=sd)
                        sd.add_refs(ref_reset_dict=new_sd.variable_refs)
                        declaration += new_dec
                        micro_result += new_tex
                    elif i.token_type == "sleep":
                        sleep_token = i
                    elif i.token_type == "child" or i.token_type == "blob":
                        micro_result += i.actual_repr(parent_str)

                else:
                    new_routine_var = next(self.NewRoutine)
                    new_routine_var_declare = self.declare(new_routine_var, vartype="unsigned char")
                    new_tex = self.group_routine(i, new_routine_var, parent_str=parent_str)

                    self.variable_refs.append(new_routine_var)
                    sd.add_refs(ref_reset_dict={new_routine_var: self.default_var_value})
                    micro_result += new_tex
                    declaration += new_routine_var_declare
            if sleep_token is not None:
                new_sd, new_dec, micro_result = self.translate_sleep(sleep_token, micro_result, parent_str, sd)
                sd.add_refs(ref_reset_dict=new_sd.variable_refs)
                declaration += new_dec
            result += micro_result
        return sd, declaration, result
    
    def translate_reserved(self, txt: str, sd=scope_data) -> tuple[str, str, str]:
        reg_matches = re.finditer(self.regex_reserved_start, txt)       # this was changed from regex_if_else
        new_dec = ""
        new_tex = ""
        scope_type = "if"
        if re.match("else", txt.strip()):
            scope_type = "else"
        elif re.match("for", txt.strip()):
            scope_type = "for"
        elif re.match("while", txt.strip()):
            scope_type = "while"
        # redundant switch statement ???
        match scope_type:
            case "if":
                new_sd, new_dec, new_tex = self.translate_if(reg_matches, txt, sd=sd)
            case "else":
                new_sd, new_dec, new_tex = self.translate_else(reg_matches, txt, sd=sd)
            case "while":
                new_sd, new_dec, new_tex = self.translate_while(reg_matches, txt, sd=sd)
            case "for":
                new_sd, new_dec, new_tex = self.translate_for(reg_matches, txt, sd=sd)
        sd.add_refs(ref_reset_dict=new_sd.variable_refs)
        return sd, new_dec, new_tex

    def _rec_translate(self, scope: str, sd=scope_data) -> tuple[str, str, str]:
        declaration = ""
        new_tex = ""
        scp = self.get_inner_scope(scope, sd=sd)
        if any(j.token_type == "parent" or j.token_type == "sleep" for j in scp):
            mscp = self.scope_to_micro_scopes(scp)
            new_sd, new_dec, new_tex = self.translate_microscopes(mscp, scope, sd=sd)
            sd.add_refs(ref_reset_dict=new_sd.variable_refs)
            declaration = new_dec
        elif any(j.token_type == "blob" for j in scp):      # blob is not routineable so this is fine i guess
            new_tex = scp[0].actual_repr("")    # is a blob so parent_str doesnt matter
        else:
            if all(j.token_type == "child" for j in scp):
                new_routine_var = next(self.NewRoutine)
                new_routine_declare = self.declare(new_routine_var, vartype="unsigned char")
                rtn = self.group_routine(scp, new_routine_var, parent_str=scope)

                self.variable_refs.append(new_routine_var)
                sd.add_refs(ref_reset_dict={new_routine_var: self.default_var_value})
                declaration = new_routine_declare
                new_tex = rtn
            else:       # blob should go here
                new_tex = scope
        return sd, declaration, new_tex

    def translate_else(self, else_lines: Match, txt: str, sd=scope_data) -> tuple[str, str, str]:
        for i in else_lines:
            inner_scope = self.match_brackets(txt, only_first=True)[1:-1].strip()
            new_sd, declaration, new_tex = self._rec_translate(inner_scope, sd=sd)
            sd.add_refs(ref_reset_dict=new_sd.variable_refs)

            res_tex = f" else {{ {new_tex} }}"
            return sd, declaration, res_tex

    def translate_if(self, if_lines: Match, txt: str, sd=scope_data) -> tuple[str, str, str]:
        for i in if_lines:
            condition_var = next(self.NewCond)
            condition_var_checker = f"{condition_var}_c"
            declare_condition_var = self.declare(condition_var, vartype="unsigned char")
            declare_condition_var_checker = self.declare(condition_var_checker, vartype="unsigned char")
            declaration = f"{declare_condition_var} {declare_condition_var_checker}"
            inner_scope = self.match_brackets(txt, only_first=True)[1:-1].strip()
            condition_line = re.sub("\)( )*\{", "", re.sub("if( )*\(", "", txt[i.start():i.end()]))

            self.variable_refs.extend([condition_var, condition_var_checker])
            new_tex = ""
            new_sd, new_dec, new_tex = self._rec_translate(inner_scope, sd=sd)
            declaration += new_dec

            sd.add_refs(ref_reset_dict={condition_var: self.default_var_value, condition_var_checker: self.default_var_value})
            sd.add_refs(ref_reset_dict=new_sd.variable_refs)
            
            a = f"if ({condition_var_checker} == 0) {{ if ({condition_line}) {{ {condition_var} = 1; }} {condition_var_checker} = 1; }}"
            b = f"if ({condition_var} == 1) {{ {new_tex} }}"
            
            return sd, declaration, f"{a} {b}"
    
    def translate_while(self, while_lines: Match, txt: str, sd=scope_data) -> tuple[str, str, str]:
        for i in while_lines:

            condition_line = re.sub("\)( )*\{", "", re.sub("while( )*\(", "", txt[i.start():i.end()]))
            inner_scope = self.match_brackets(txt, only_first=True)[1:-1].strip()

            is_sleeped = True if re.search(self.regex_sleep, inner_scope) is not None else False
            if is_sleeped:
                new_sd, new_dec, new_tex = self._sleeped_translate_while(inner_scope, condition_line, sd=sd)
            else:
                new_sd, new_dec, new_tex = self._blocking_translate_while(inner_scope, condition_line, sd=sd)
            sd.add_refs(ref_reset_dict=new_sd.variable_refs)
            return sd, new_dec, new_tex
    
    def _blocking_translate_while(self, inner_scope: str, condition_line: str, sd=scope_data) -> tuple[str, str, str]:
        declaration = ""
        new_tex = inner_scope

        loopvar = next(self.NewLoopVar)
        loopvar_declare = self.declare(loopvar, vartype="unsigned char")
        self.variable_refs.append(loopvar)
        sd.add_refs(ref_reset_dict={loopvar: self.default_var_value})

        a = f"if ({loopvar} == 0) {{ while ({condition_line}) {{ {new_tex} }} {loopvar} = 1; }}"
        declaration += loopvar_declare

        return sd, declaration, a

    def _sleeped_translate_while(self, inner_scope: str, condition_line: str, sd=scope_data) -> tuple[str, str, str]:
        declaration = ""

        loopvar = next(self.NewLoopVar)
        loopvar_declare = self.declare(loopvar, vartype="unsigned char")
        break_swap = next(self.NewStrSwap)
        continue_swap = next(self.NewStrSwap)

        # placeholder for break and continue statement replacements
        # updating main sd
        sub_dict = {"break": f"${self.swp}{break_swap}$", "continue": f"${self.swp}{continue_swap}$"}
        sd.add_subs(sub_dict=sub_dict)
        # removing duplicates from new_sd, so that it only contains refs from its own scope
        old_sd_vars = list(sd.variable_refs.keys())
        new_sd, new_dec, new_tex = self._rec_translate(inner_scope, sd=sd)
        new_sd.delete_dup_refs(old_sd_vars)
        # adding new_sd variables to the main sd obj
        sd.add_refs(ref_reset_dict=new_sd.variable_refs)
        sd.add_refs(ref_reset_dict={loopvar: self.default_var_value})
        self.variable_refs.append(loopvar)        
       
        vars_to_reset = {}
        # creating local loop resets according to new_sd because those are the inner loop scope vars
        for k, v in new_sd.variable_refs.items():
            if re.match(self.regex_reset_every_loop_vars, k) is not None:
                vars_to_reset[k] = v
        scope_vars_reset = self.reset_vars(vars_to_reset)

        new_tex = re.sub(f"\${self.swp}({break_swap})\$", f"{loopvar} = 1; return;", new_tex)
        new_tex = re.sub(f"\${self.swp}({continue_swap})\$", f"{scope_vars_reset} return;", new_tex)

        a = f"if ({loopvar} == 0) {{ if ({condition_line}) {{ {new_tex} {scope_vars_reset} return; }} else {{ {loopvar} = 1; }} }}"

        declaration += loopvar_declare
        declaration += new_dec

        return sd, declaration, a

    def translate_for(self, for_lines: Match, txt: str, sd=scope_data) -> tuple[str, str, str]:
        for i in for_lines:
            condition_line = re.sub("\)( )*\{", "", re.sub("for( )*\(", "", txt[i.start():i.end()]))
            for_parts = condition_line.split(";")
            fdt = re.match(self.regex_for_declare_type_start, for_parts[0]).group().strip()
            fdn = re.search(self.regex_for_declare_name_start, for_parts[0]).group().strip()[len(fdt):-1].strip()
            fdv = re.search(self.regex_for_declare_value_start, for_parts[0]).group()[1:].strip()

            inner_scope = self.match_brackets(txt, only_first=True)[1:-1].strip()
            is_sleeped = True if re.search(self.regex_sleep, inner_scope) is not None else False
            if is_sleeped:
                new_sd, new_dec, new_tex = self._sleeped_translate_for(inner_scope, for_parts, fdt, fdn, fdv, sd)
            else:
                new_sd, new_dec, new_tex = self._blocking_translate_for(inner_scope, condition_line, fdn, sd)
            sd.add_refs(ref_reset_dict=new_sd.variable_refs)
            return sd, new_dec, new_tex

    def _blocking_translate_for(self, inner_scope: str, condition_line: str, fdn: str, sd=scope_data) -> tuple[str, str, str]:
        declaration = ""
        # new_dec, new_tex = self._rec_translate(inner_scope)   # this is not needed because its blocking
        new_dec = ""

        for_iter = next(self.NewIter)
        loopvar = next(self.NewLoopVar)
        loopvar_declare = self.declare(loopvar, vartype="unsigned char")
        self.variable_refs.append(loopvar)
        sd.add_refs(ref_reset_dict={loopvar: self.default_var_value})
        #replace old vars with new ones
        new_tex = self.sub_var(inner_scope, fdn, for_iter)
        condition_line = self.sub_var(condition_line, fdn, for_iter)

        a = f"if ({loopvar} == 0) {{ for ({condition_line}) {{ {new_tex} }} {loopvar} = 1; }}"

        declaration += new_dec
        declaration += loopvar_declare

        return sd, declaration, a

    def _sleeped_translate_for(self, inner_scope: str, for_parts: list[str], fdt, fdn, fdv, sd=scope_data) -> tuple[str, str]:
        declaration = ""

        for_iter = next(self.NewIter)
        loopvar = next(self.NewLoopVar)
        self.variable_refs.extend([for_iter, loopvar])
        sd.add_refs(ref_reset_dict={for_iter: fdv, loopvar: self.default_var_value})
        fcond = self.sub_var(for_parts[1], fdn, for_iter)
        fadvance = self.sub_var(for_parts[2], fdn, for_iter)
        # replace old vars with new ones
        inner_scope = self.sub_var(inner_scope, fdn, for_iter)

        break_swap = next(self.NewStrSwap)
        continue_swap = next(self.NewStrSwap)

        # placeholder for break and continue statement replacements
        sub_dict = {"break": f"${self.swp}{break_swap}$", "continue": f"${self.swp}{continue_swap}$"}
        sd.add_subs(sub_dict=sub_dict)
        old_sd_vars = list(sd.variable_refs.keys())
        new_sd, new_dec, new_tex = self._rec_translate(inner_scope, sd=sd)
        new_sd.delete_dup_refs(old_sd_vars)
        sd.add_refs(ref_reset_dict=new_sd.variable_refs)
        
        vars_to_reset = {}
        # removing references that should not be reset every loop
        for k, v in new_sd.variable_refs.items():
            if re.match(self.regex_reset_every_loop_vars, k) is not None:
                vars_to_reset[k] = v
        scope_vars_reset = self.reset_vars(vars_to_reset)
        
        # swapping actual break and continue statement replacements
        new_tex = re.sub(f"\${self.swp}({break_swap})\$", f"{loopvar} = 1; return;", new_tex)
        new_tex = re.sub(f"\${self.swp}({continue_swap})\$", f"{scope_vars_reset}{fadvance}; return;", new_tex)

        a = f"if ({loopvar} == 0) {{ if ({fcond}) {{ {new_tex} {scope_vars_reset}{fadvance}; return; }} else {{ {loopvar} = 1; }} }}"
        declaration += self.declare(for_iter, vartype=fdt, val=fdv)
        declaration += self.declare(loopvar, vartype="unsigned char")
        declaration += new_dec
        
        return sd, declaration, a

    def wrap_func(self, func_content: str):
        func_name = next(self.NewFunc)
        return f"void {func_name}() {{ {func_content} }}", func_name

    def purify_input(self, s: str) -> str:
        # TODO split with shlex
        return " ".join(s.strip().split())     # cleaning string before using it

    def get_large_scopes(self, txt: str) -> tuple[str]:
        txt = self.purify_input(txt)
        setup_match = re.search(self.regex_setup, txt)
        loop_match = re.search(self.regex_loop, txt)
        a = self.match_brackets(txt[setup_match.end()-1:], only_first=True, get_index=True)
        b = self.match_brackets(txt[loop_match.end()-1:], only_first=True, get_index=True)
        setup = (setup_match.start(), setup_match.end() + a[1])
        loop = (loop_match.start(), loop_match.end() + b[1])
        if setup[0] < loop[0]:
            other_content = txt[:setup[0]] + txt[setup[1]:loop[0]] + txt[loop[1]:]
        else:
            other_content = txt[:loop[0]] + txt[loop[1]:setup[0]] + txt[setup[1]:]
        setup_content = txt[setup_match.end()-1:setup_match.end() + a[1]].strip()[1:-1].strip()
        loop_content = txt[loop_match.end()-1:loop_match.end() + b[1]].strip()[1:-1].strip()
        
        return other_content, setup_content, loop_content

    def thread_token_to_str(self, tkn: lang_token, parent_str="") -> str:
        if parent_str == "":
            parent_str = self.input_code
        res = re.sub("thread( )*\{", "", tkn.actual_repr(parent_str).strip()[:-1], 1).strip()
        return res

    def _interpret_thread(self, tkn: lang_token, parent_str="") -> str:
        tkn_str = self.thread_token_to_str(tkn, parent_str=parent_str)
        scp = self.get_inner_scope(tkn_str, sd=scope_data())    # lazily just putting a scope_data in there, its meaningless
        microscopes = self.scope_to_micro_scopes(scp)
        new_sd = scope_data()
        sd, v_dec, tex = self.translate_microscopes(microscopes, tkn_str, sd=new_sd)
        vars_reset = self.reset_vars(self.variable_refs)
        f_dec, func_name = self.wrap_func(f"{tex} {vars_reset}")
        self.variable_refs = []     # emptying the refs before starting another thread scope
        return v_dec, f_dec, func_name

    def _finalize(self, func_declaration, var_declaration, setup_code, main_loop_code, other_code):
        update_main_timer = f"{self.main_timer} = millis(); "
        declare_main_timer = f"unsigned long {self.main_timer} = 0;"
        # _sleep = "sleep(1); " if self.has_sleep else ""
        res = f"{other_code} {declare_main_timer} {var_declaration} {func_declaration} void setup() {{ {setup_code} }} void loop() {{ {update_main_timer} {main_loop_code} }}"
        return res

    def interpret(self, txt: str) -> str:
        txt = self.purify_input(txt)
        self.input_code = txt

        var_declaration = ""
        func_declaration = ""
        main_loop_code = ""
        
        other_code, setup_scope, loop_scope = self.get_large_scopes(txt)
        thread_scopes = self.get_inner_scope(loop_scope, sd=scope_data())     # this scope_data is meaningless and im lazy
        for tkn in thread_scopes:
            v_dec, f_dec, func_name = self._interpret_thread(tkn, parent_str=loop_scope)
            tex = f"{func_name}();"
            v_dec += self.user_custom_variables.get_dec()
            for oldvar, newvar in self.custom_var_declaration(self.user_custom_variables).items():
                v_dec = self.sub_var(v_dec, oldvar, newvar)
                f_dec = self.sub_var(f_dec, oldvar, newvar)
            func_declaration += f_dec
            var_declaration += v_dec
            main_loop_code += tex
            self.user_custom_variables = ParsedDeclaration()        # clearing custom vars before interpreting next thread

        # sort decleration of vars
        sorted_d = var_declaration.strip().split(";")
        sorted_d = [i.strip() for i in sorted_d]
        if "" in sorted_d:
            sorted_d.remove("")
        # sorted_d.sort(key=lambda x: x[0:7])
        sorted_d.sort()

        var_declaration = "".join(f"{i.strip()}; " for i in sorted_d)

        result_code = self._finalize(func_declaration, var_declaration, setup_scope, main_loop_code, other_code)

        return result_code


if __name__ == "__main__":
    inp = """
    void setup() {
        pinMode(7, OUTPUT);
        pinMode(5, OUTPUT);
    }
    void loop() {
        thread {
            int i = 50;
            sleep(i);
            digitalWrite(7, HIGH);
            sleep(i);
            digitalWrite(7, LOW);
        }
        thread {
            int i = 450;
            sleep(i);
            digitalWrite(5, HIGH);
            sleep(i);
            digitalWrite(5, LOW);
        }
    }
    """


    interp = Interpreter()
    res = interp.interpret(inp)
    print(res)
