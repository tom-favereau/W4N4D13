open Cil

module E = Errormsg

let loc = Cil.locUnknown


type opcode =
  | OP_NOP
  | OP_PUSH
  | OP_LOAD
  | OP_STORE
  | OP_POP
  | OP_ADD
  | OP_SUB
  | OP_MUL
  | OP_DIV
  | OP_MOD
  | OP_LT
  | OP_GT
  | OP_LE
  | OP_GE
  | OP_EQ
  | OP_NE
  | OP_AND
  | OP_OR
  | OP_BAND
  | OP_BOR
  | OP_BXOR
  | OP_SHL
  | OP_SHR
  | OP_NEG
  | OP_NOT
  | OP_BNOT
  | OP_JMP
  | OP_JZ
  | OP_JNZ
  | OP_CALL      (* internal call *)
  | OP_CALLX     (* extern call *)
  | OP_RET
  | OP_RET0

let opcode_to_text = function
  | OP_NOP -> "NOP"
  | OP_PUSH -> "PUSH"
  | OP_LOAD -> "LOAD"
  | OP_STORE -> "STORE"
  | OP_POP -> "POP"
  | OP_ADD -> "ADD"
  | OP_SUB -> "SUB"
  | OP_MUL -> "MUL"
  | OP_DIV -> "DIV"
  | OP_MOD -> "MOD"
  | OP_LT -> "LT"
  | OP_GT -> "GT"
  | OP_LE -> "LE"
  | OP_GE -> "GE"
  | OP_EQ -> "EQ"
  | OP_NE -> "NE"
  | OP_AND -> "AND"
  | OP_OR -> "OR"
  | OP_BAND -> "BAND"
  | OP_BOR -> "BOR"
  | OP_BXOR -> "BXOR"
  | OP_SHL -> "SHL"
  | OP_SHR -> "SHR"
  | OP_NEG -> "NEG"
  | OP_NOT -> "NOT"
  | OP_BNOT -> "BNOT"
  | OP_JMP -> "JMP"
  | OP_JZ -> "JZ"
  | OP_JNZ -> "JNZ"
  | OP_CALL -> "CALL"
  | OP_CALLX -> "CALLX"
  | OP_RET -> "RET"
  | OP_RET0 -> "RET0"

type operand =
  | OImm of int
  | OLabel of int

type vinstr =
  | IOp of opcode * operand list
  | ILabel of int

type vprog = vinstr list

let fresh_label =
  let c = ref 0 in
  fun () -> incr c; !c

let fail s =
  E.error "%s" s;
  raise (Failure "virtualize")

let find_opt pred lst =
  let rec go = function
    | [] -> None
    | x :: xs -> if pred x then Some x else go xs
  in
  go lst


let encode_opcodes = true

let opcode_list : opcode list = [
  OP_NOP; OP_PUSH; OP_LOAD; OP_STORE; OP_POP;
  OP_ADD; OP_SUB; OP_MUL; OP_DIV; OP_MOD;
  OP_LT; OP_GT; OP_LE; OP_GE; OP_EQ; OP_NE;
  OP_AND; OP_OR; OP_BAND; OP_BOR; OP_BXOR;
  OP_SHL; OP_SHR; OP_NEG; OP_NOT; OP_BNOT;
  OP_JMP; OP_JZ; OP_JNZ; OP_CALL; OP_CALLX;
  OP_RET; OP_RET0;
]

let opcode_count = List.length opcode_list

let opcode_to_int (op: opcode) : int =
  let rec idx i = function
    | [] -> fail "Virtualize: opcode inconnu"
    | x::xs -> if x = op then i else idx (i+1) xs
  in
  idx 0 opcode_list

let int_to_opcode (i: int) : opcode =
  let rec nth n = function
    | [] -> fail "Virtualize: opcode index invalide"
    | x::xs -> if n = 0 then x else nth (n-1) xs
  in
  nth i opcode_list

let rec gcd a b =
  if b = 0 then abs a else gcd b (a mod b)

(*params enc, must be the same in the vm*)
let p1 = 5
let p2 = 7
let a_pc = 11
let b_pc = 3


let modn x =
  let r = x mod opcode_count in
  if r < 0 then r + opcode_count else r

let encode_opcode ~(pc:int) (op: opcode) : opcode =
  if not encode_opcodes then op
  else
    let op_i = opcode_to_int op in
    let fpc = modn (a_pc * pc + b_pc) in
    let enc = modn (p1 * op_i + p2 + fpc) in
    int_to_opcode enc

(*externs callable*)
let externs : (string * int) list =
  [
    ("puts", 0);
    ("printf", 1);
    ("printf2", 2);
    ("printf3", 3);
    ("printi", 4);
    ("rand", 5);
    ("system", 6);
    ("getKeya", 7);
    ("getKeyb", 8);
    ("getKeyc", 9);
    ("getKeyd", 10);
    ("getLen", 11);
  ]

let extern_id name =
  try List.assoc name externs
  with Not_found ->
    fail ("Virtualize: call externe non declaree: " ^ name)


let exp_of_lval lv = Lval lv
let lv_var vi = (Var vi, NoOffset)
let exp_var vi = exp_of_lval (lv_var vi)
let lv_index vi idx = (Var vi, Index (idx, NoOffset))
let exp_index vi idx = exp_of_lval (lv_index vi idx)


type venv = {
  var_index : (int, int) Hashtbl.t; 
  var_count : int;
  mutable temp_count : int;
  stmt_label : (stmt, int) Hashtbl.t; 
}

let build_var_env (fd: fundec) : venv =
  let all = fd.sformals @ fd.slocals in
  let tbl = Hashtbl.create (List.length all) in
  List.iteri (fun i v -> Hashtbl.add tbl v.vid i) all;
  {
    var_index = tbl;
    var_count = List.length all;
    temp_count = 0;
    stmt_label = Hashtbl.create 17;
  }

let index_of_var env (v: varinfo) : int =
  try Hashtbl.find env.var_index v.vid
  with Not_found ->
    fail "Virtualize: variable non locale non supportee"

let fresh_temp (env: venv) : int =
  let idx = env.var_count + env.temp_count in
  env.temp_count <- env.temp_count + 1;
  idx

let ensure_stmt_label (env: venv) (s: stmt) : int =
  try Hashtbl.find env.stmt_label s
  with Not_found ->
    let l = fresh_label () in
    Hashtbl.add env.stmt_label s l;
    l

let stmt_has_c_label (s: stmt) : bool =
  List.exists (function
    | Label _ -> true
    | _ -> false
  ) s.labels

let stmt_goto_label_instrs (env: venv) (s: stmt) : vinstr list =
  let lbl_opt =
    if stmt_has_c_label s then Some (ensure_stmt_label env s)
    else if Hashtbl.mem env.stmt_label s then Some (Hashtbl.find env.stmt_label s)
    else None
  in
  match lbl_opt with
  | None -> []
  | Some l -> [ ILabel l ]


type vstate = {
  strings : (string, int) Hashtbl.t;
  mutable str_list_rev : (int * string) list;
  mutable next_str_id : int;
}

let new_state () =
  { strings = Hashtbl.create 17; str_list_rev = []; next_str_id = 0 }

let get_str_id (st: vstate) (s: string) : int =
  try Hashtbl.find st.strings s
  with Not_found ->
    let id = st.next_str_id in
    st.next_str_id <- st.next_str_id + 1;
    Hashtbl.add st.strings s id;
    st.str_list_rev <- (id, s) :: st.str_list_rev;
    id

let escape_str (s: string) : string =
  let b = Buffer.create (String.length s + 8) in
  String.iter (function
    | '\\' -> Buffer.add_string b "\\\\"
    | '"'  -> Buffer.add_string b "\\\""
    | '\n' -> Buffer.add_string b "\\n"
    | '\t' -> Buffer.add_string b "\\t"
    | '\r' -> Buffer.add_string b "\\r"
    | c -> Buffer.add_char b c
  ) s;
  Buffer.contents b


let int_of_const = function
  | CInt64 (i, _, _) -> Int64.to_int i
  | CChr c -> int_of_char c
  | CEnum (e, _, _) -> (*to delete*)
      (match e with
       | Const (CInt64 (i, _, _)) -> Int64.to_int i
       | _ -> fail "Virtualize: enum non supporte")
  | _ -> fail "Virtualize: constante non supportee"

let is_int_or_ptr_type t =
  match unrollType t with
  | TInt _ -> true
  | TPtr _ -> true
  | _ -> false

let binop_to_opcode = function
  | PlusA -> OP_ADD
  | MinusA -> OP_SUB
  | Mult -> OP_MUL
  | Div -> OP_DIV
  | Mod -> OP_MOD
  | Lt -> OP_LT
  | Gt -> OP_GT
  | Le -> OP_LE
  | Ge -> OP_GE
  | Eq -> OP_EQ
  | Ne -> OP_NE
  | LAnd -> OP_AND
  | LOr -> OP_OR
  | BAnd -> OP_BAND
  | BOr -> OP_BOR
  | BXor -> OP_BXOR
  | Shiftlt -> OP_SHL
  | Shiftrt -> OP_SHR
  | _ -> fail "Virtualize: binop non supporte"

let unop_to_opcode = function
  | Neg -> OP_NEG
  | LNot -> OP_NOT
  | BNot -> OP_BNOT
  | _ -> fail "Virtualize: unop non supporte"

let rec compile_exp (env: venv) (st: vstate) (e: exp) : vprog =
  match e with
  | Const (CStr s) ->
      let id = get_str_id st s in
      [ IOp (OP_PUSH, [OImm id]) ]

  | Const c ->
      [ IOp (OP_PUSH, [OImm (int_of_const c)]) ]

  | Lval (Var v, NoOffset) ->
      if v.vglob then fail "Virtualize: acces global non supporte";
      [ IOp (OP_LOAD, [OImm (index_of_var env v)]) ]

  | Lval _ ->
      fail "Virtualize: lval non supporte"

  | UnOp (op, e1, _) ->
      compile_exp env st e1 @ [ IOp (unop_to_opcode op, []) ]

  | BinOp (op, e1, e2, _) ->
      compile_exp env st e1 @ compile_exp env st e2 @
      [ IOp (binop_to_opcode op, []) ]

  | CastE (t, e1) ->
      if is_int_or_ptr_type t then compile_exp env st e1
      else fail "Virtualize: cast non supporte"

  | _ ->
      fail "Virtualize: expression non supportee"


type fmeta = {
  f_label : int;
  f_formals : int;
  f_is_va : bool;
}

let fun_signature (fd: fundec) : (int * bool) =
  match unrollType fd.svar.vtype with
  | TFun (_, args_opt, isva, _) ->
      let nformals =
        match args_opt with
        | None -> List.length fd.sformals
        | Some args -> List.length args
      in
      (nformals, isva)
  | _ -> fail "Virtualize: type fonction invalide"


type cctx = {
  break_lbl : int option;
  continue_lbl : int option;
  ret_is_void : bool;
}


let case_value_of_exp = function
  | Const c -> int_of_const c
  | _ -> fail "Virtualize: case non constant"

let collect_switch_labels (b: block)
  : ((stmt, int list) Hashtbl.t * (int * int) list * int option) =
  let label_map : (stmt, int list) Hashtbl.t = Hashtbl.create 17 in
  let cases = ref [] in
  let default = ref None in
  let seen_cases : (int, unit) Hashtbl.t = Hashtbl.create 17 in

  List.iter (fun s ->
    let lbls = ref [] in
    List.iter (function
      | Case (e, _) ->
          let v = case_value_of_exp e in
          if Hashtbl.mem seen_cases v then
            fail "Virtualize: case duplique dans switch";
          Hashtbl.add seen_cases v ();
          let l = fresh_label () in
          cases := (v, l) :: !cases;
          lbls := l :: !lbls
      | Default _ ->
          (match !default with
           | Some _ -> fail "Virtualize: multiple default dans switch"
           | None ->
               let l = fresh_label () in
               default := Some l;
               lbls := l :: !lbls)
      | _ -> ()
    ) s.labels;
    if !lbls <> [] then
      Hashtbl.add label_map s (List.rev !lbls)
  ) b.bstmts;

  (label_map, List.rev !cases, !default)


let rec compile_stmt (env: venv) (st: vstate) (ctx: cctx)
    (fmap: (string, fmeta) Hashtbl.t) (s: stmt) : vprog =
  match s.skind with
  | Instr il ->
      List.flatten (List.map (compile_instr env st ctx fmap) il)

  | If (e, tb, fb, _) ->
      let l_then = fresh_label () in
      let l_else = fresh_label () in
      let l_end = fresh_label () in
      compile_exp env st e @
      [ IOp (OP_JNZ, [OLabel l_then]);
        IOp (OP_JMP, [OLabel l_else]);
        ILabel l_then ] @
      compile_block env st ctx fmap tb @
      [ IOp (OP_JMP, [OLabel l_end]);
        ILabel l_else ] @
      compile_block env st ctx fmap fb @
      [ ILabel l_end ]

  | Switch (e, b, _, _) ->
      let l_end = fresh_label () in
      let ctx' = { ctx with break_lbl = Some l_end } in
      let tmp = fresh_temp env in
      let (label_map, cases, default_lbl) = collect_switch_labels b in
      let eval =
        compile_exp env st e @
        [ IOp (OP_STORE, [OImm tmp]) ]
      in
      let cmp =
        List.flatten (List.map (fun (v, l) ->
          [ IOp (OP_LOAD, [OImm tmp]);
            IOp (OP_PUSH, [OImm v]);
            IOp (OP_EQ, []);
            IOp (OP_JNZ, [OLabel l]) ]
        ) cases)
      in
      let jdef =
        match default_lbl with
        | Some l -> [ IOp (OP_JMP, [OLabel l]) ]
        | None -> [ IOp (OP_JMP, [OLabel l_end]) ]
      in
      eval @ cmp @ jdef @
      compile_block_with_label_map env st ctx' fmap b label_map @
      [ ILabel l_end ]

  | Loop (b, _, cont_opt, _) ->
      let l_head = fresh_label () in
      let l_cont = fresh_label () in
      let l_end = fresh_label () in
      let ctx' = { ctx with break_lbl = Some l_end; continue_lbl = Some l_cont } in
      let body_code =
        match cont_opt with
        | Some s -> compile_block_with_label env st ctx' fmap b (Some (s, l_cont))
        | None -> compile_block env st ctx' fmap b
      in
      [ ILabel l_head ] @
      body_code @
      (match cont_opt with None -> [ ILabel l_cont ] | Some _ -> []) @
      [ IOp (OP_JMP, [OLabel l_head]);
        ILabel l_end ]

  | Block b ->
      compile_block env st ctx fmap b

  | Break _ ->
      (match ctx.break_lbl with
       | Some l -> [ IOp (OP_JMP, [OLabel l]) ]
       | None -> fail "Virtualize: break hors boucle")

  | Continue _ ->
      (match ctx.continue_lbl with
       | Some l -> [ IOp (OP_JMP, [OLabel l]) ]
       | None -> fail "Virtualize: continue hors boucle")

  | Goto (sref, _) ->
      let l = ensure_stmt_label env !sref in
      [ IOp (OP_JMP, [OLabel l]) ]

  | Return (None, _) ->
      if ctx.ret_is_void then [ IOp (OP_RET0, []) ]
      else [ IOp (OP_RET0, []) ]

  | Return (Some e, _) ->
      compile_exp env st e @ [ IOp (OP_RET, []) ]

  | _ ->
      fail "Virtualize: statement non supporte"

and compile_block (env: venv) (st: vstate) (ctx: cctx)
    (fmap: (string, fmeta) Hashtbl.t) (b: block) : vprog =
  compile_block_with_label env st ctx fmap b None

and compile_block_with_label (env: venv) (st: vstate) (ctx: cctx)
    (fmap: (string, fmeta) Hashtbl.t)
    (b: block) (target: (stmt * int) option) : vprog =
  let found = ref false in
  let code =
    List.flatten (List.map (fun s ->
      let lbl_target =
        match target with
        | Some (ts, l) when ts == s ->
            found := true; [ ILabel l ]
        | _ -> []
      in
      let lbl_goto = stmt_goto_label_instrs env s in
      lbl_target @ lbl_goto @ compile_stmt env st ctx fmap s
    ) b.bstmts)
  in
  match target with
  | Some (_, l) when not !found ->
      code @ [ ILabel l ]
  | _ -> code

and compile_block_with_label_map (env: venv) (st: vstate) (ctx: cctx)
    (fmap: (string, fmeta) Hashtbl.t)
    (b: block) (label_map: (stmt, int list) Hashtbl.t) : vprog =
  List.flatten (List.map (fun s ->
    let lbls =
      try Hashtbl.find label_map s
      with Not_found -> []
    in
    let lbl_code = List.map (fun l -> ILabel l) lbls in
    let lbl_goto = stmt_goto_label_instrs env s in
    lbl_code @ lbl_goto @ compile_stmt env st ctx fmap s
  ) b.bstmts)

and compile_instr (env: venv) (st: vstate) (_ctx: cctx)
    (fmap: (string, fmeta) Hashtbl.t) (i: Cil.instr) : vprog =
  match i with
  | Set ((Var v, NoOffset), e, _) ->
      if v.vglob then fail "Virtualize: assign global non supporte";
      compile_exp env st e @
      [ IOp (OP_STORE, [OImm (index_of_var env v)]) ]

  | Set _ ->
      fail "Virtualize: lval non supporte"

  | Call (retopt, Lval (Var f, NoOffset), args, _) ->
      let argc = List.length args in
      let args_code = List.flatten (List.map (compile_exp env st) args) in

      if Hashtbl.mem fmap f.vname then
        let fm = Hashtbl.find fmap f.vname in
        if (not fm.f_is_va) && (argc <> fm.f_formals) then
          fail ("Virtualize: arite invalide pour " ^ f.vname);

        let call = IOp (OP_CALL, [OLabel fm.f_label; OImm argc]) in
        (match retopt with
         | None ->
             args_code @ [call; IOp (OP_POP, [])]
         | Some (Var v, NoOffset) ->
             if v.vglob then fail "Virtualize: assign global non supporte";
             args_code @ [call; IOp (OP_STORE, [OImm (index_of_var env v)])]
         | Some _ ->
             fail "Virtualize: lval non supporte")
      else
        let id =
             if f.vname = "printf" then
                match argc with
                    | 2 -> extern_id "printf"   
                    | 3 -> extern_id "printf2"  
                    | 4 -> extern_id "printf3"  (*add more*)
                    | _ -> fail "printf arity not supported"
                else
                    extern_id f.vname
        in
        let call = IOp (OP_CALLX, [OImm id; OImm argc]) in
        (match retopt with
         | None ->
             args_code @ [call; IOp (OP_POP, [])]
         | Some (Var v, NoOffset) ->
             if v.vglob then fail "Virtualize: assign global non supporte";
             args_code @ [call; IOp (OP_STORE, [OImm (index_of_var env v)])]
         | Some _ ->
             fail "Virtualize: lval non supporte")

  | Call _ ->
      fail "Virtualize: call non supporte"

  | _ ->
      fail "Virtualize: instr non supportee"


let label_name l = "L" ^ string_of_int l

let emit_program ~(entry_label:int) ~(funcs:(string*int*int) list)
    ~(strs:(int*string) list) (p: vprog) : string =
  let lines = ref [] in
  let add s = lines := s :: !lines in

  List.iter (fun (name, lbl, locals) ->
    add (".func " ^ name ^ " " ^ label_name lbl ^ " " ^ string_of_int locals)
  ) funcs;

  List.iter (fun (id, s) ->
    add (".str " ^ string_of_int id ^ " \"" ^ escape_str s ^ "\"")
  ) strs;

  add (".entry " ^ label_name entry_label);

  let pc = ref 0 in
  List.iter (function
    | ILabel l ->
        add (label_name l ^ ":")
    | IOp (op, ops) ->
        let op_enc = encode_opcode ~pc:!pc op in
        let op_s = opcode_to_text op_enc in
        let ops_s =
          match ops with
          | [] -> ""
          | _ ->
              let os = List.map (function
                | OImm n -> string_of_int n
                | OLabel l -> label_name l
              ) ops in
              " " ^ String.concat " " os
        in
        add (op_s ^ ops_s);
        incr pc
  ) p;

  String.concat "\n" (List.rev !lines) ^ "\n"


type fcompiled = {
  c_name : string;
  c_label : int;
  c_locals : int;
  c_code : vprog;
}

let compile_fundec (fd: fundec) (fmap: (string, fmeta) Hashtbl.t) (st: vstate)
  : fcompiled =
  let env = build_var_env fd in

  let ret_is_void =
    match unrollType fd.svar.vtype with
    | TFun (rt, _, _, _) ->
        (match unrollType rt with
         | TVoid _ -> true
         | TInt _ -> false
         | _ -> fail "Virtualize: type de retour non supporte")
    | _ -> fail "Virtualize: type fonction invalide"
  in

  let ctx = { break_lbl = None; continue_lbl = None; ret_is_void } in
  let entry = (Hashtbl.find fmap fd.svar.vname).f_label in
  let body = compile_block env st ctx fmap fd.sbody in

  let prog = (ILabel entry) :: body in

  let prog =
    let rec last_op = function
      | [] -> None
      | [IOp (op, _)] -> Some op
      | [_] -> None
      | _::tl -> last_op tl
    in
    match last_op prog with
    | Some OP_RET | Some OP_RET0 -> prog
    | _ -> prog @ [IOp (OP_RET0, [])]
  in

  let locals = env.var_count + env.temp_count in
  { c_name = fd.svar.vname; c_label = entry; c_locals = locals; c_code = prog }


let pick_entry_label (fmap: (string, fmeta) Hashtbl.t) : int =
  if Hashtbl.mem fmap "main" then (Hashtbl.find fmap "main").f_label
  else
    let lbl = ref None in
    Hashtbl.iter (fun _ fm -> if !lbl = None then lbl := Some fm.f_label) fmap;
    match !lbl with
    | Some l -> l
    | None -> fail "Virtualize: aucune fonction"

let output_path ?output (file: file) : string =
  match output with
  | Some p -> p
  | None ->
      let path = file.fileName in
      let base =
        try
          let i = String.rindex path '.' in
          String.sub path 0 i
        with Not_found -> path
      in
      base ^ ".opcode"

let run ?output (file: file) : unit =
  let fundecs =
    List.fold_left (fun acc g ->
      match g with
      | GFun (fd, _) -> fd :: acc
      | _ -> acc
    ) [] file.globals
    |> List.rev
  in
  if fundecs = [] then fail "Virtualize: aucun fundec";

  let fmap : (string, fmeta) Hashtbl.t = Hashtbl.create (List.length fundecs) in
  List.iter (fun fd ->
    let (nformals, isva) = fun_signature fd in
    let lbl = fresh_label () in
    Hashtbl.add fmap fd.svar.vname { f_label = lbl; f_formals = nformals; f_is_va = isva }
  ) fundecs;

  let st = new_state () in
  let compiled = List.map (fun fd -> compile_fundec fd fmap st) fundecs in

  let entry = pick_entry_label fmap in
  let funcs =
    List.map (fun fc -> (fc.c_name, fc.c_label, fc.c_locals)) compiled
  in

  let prog =
    List.flatten (List.map (fun fc -> fc.c_code) compiled)
  in

  let strs = List.rev st.str_list_rev in
  let text = emit_program ~entry_label:entry ~funcs ~strs prog in
  let path = output_path ?output file in
  let oc = open_out path in
  output_string oc text;
  close_out oc;
  E.log "Virtualize: wrote %s\n" path
