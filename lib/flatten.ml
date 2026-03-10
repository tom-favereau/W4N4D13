open Cil

let loc = Cil.locUnknown

(*go through the ast and collect the stmt, return them*)
let collect_stmts (fd : fundec) : stmt list =
  let acc = ref [] in
  let v = object
    inherit nopCilVisitor
    method! vstmt s =
      acc := s :: !acc;
      DoChildren
  end in
  ignore (visitCilFunction (v :> cilVisitor) fd);
  !acc

(*we do not support switch*)
let has_bad_label (s : stmt) : bool =
  List.exists (function
    | Label (_, _, from_source) when from_source -> true
    | Case _ | CaseRange _ | Default _ -> true
    | _ -> false
  ) s.labels

let is_supported_stmt (s : stmt) : bool =
  if has_bad_label s then false else
  match s.skind with
  | ComputedGoto _ | Switch _ | TryFinally _ | TryExcept _ -> false
  | _ -> true

(*check the coherence of the ast*)
let succs_ok (s : stmt) : bool =
  match s.skind with
  | If _ ->
      let n = List.length s.succs in
      n = 1 || n = 2
  | Return _ -> s.succs = []
  | Goto _ -> List.length s.succs = 1
  | _ -> List.length s.succs <= 1

(*List.hd_opt is not available in my version of ocaml, same for some other functions, hence why I rewrite some*)
let block_entry (b : block) : stmt option =
  match b.bstmts with
  | s::_ -> Some s
  | [] -> None

let pick_succ_not (succs : stmt list) (avoid : stmt) : stmt option =
  let rec aux = function
    | [] -> None
    | s::tl -> if s.sid <> avoid.sid then Some s else aux tl
  in
  aux succs

let resolve_if_targets (s : stmt) (tb : block) (fb : block) : stmt * stmt =
  let succs = s.succs in
  let then_entry = block_entry tb in
  let else_entry = block_entry fb in
  let fallthrough =
    match succs with
    | s1::_ -> s1
    | [] -> s
  in
  let then_target =
    match then_entry with
    | Some t -> t
    | None ->
        (match else_entry with
         | Some e ->
             (match pick_succ_not succs e with
              | Some ft -> ft
              | None -> fallthrough)
         | None -> fallthrough)
  in
  let else_target =
    match else_entry with
    | Some e -> e
    | None ->
        (match then_entry with
         | Some t ->
             (match pick_succ_not succs t with
              | Some ft -> ft
              | None -> fallthrough)
         | None -> fallthrough)
  in
  (then_target, else_target)

(*we use Control Flow Graph given by the CIL API*)
let flatten (fd : fundec) : unit =
  Cil.prepareCFG fd;
  Cil.computeCFGInfo fd false;

  let stmts = collect_stmts fd in
  if stmts = [] then () else
  if (List.for_all is_supported_stmt stmts && List.for_all succs_ok stmts)
  then begin
    let state_vi = makeTempVar fd ~name:"__state" intType in
    let mk_set_state (k : int) : stmt =
      let lv = Var state_vi, NoOffset in
      let i = Set (lv, integer k, loc) in
      mkStmt (Instr [i])
    in
    let mk_case_from_body (state : int) (body : stmt list) (need_break : bool) : stmt =
      let break_stmt = mkStmt (Break loc) in
      let stmts = if need_break then body @ [break_stmt] else body in
      let b = mkBlock stmts in
      let s = mkStmt (Block b) in
      s.labels <- [Case (integer state, loc)];
      s
    in

    let stmts = List.sort (fun a b -> compare a.sid b.sid) stmts in
    let sid_to_state = Hashtbl.create (List.length stmts) in
    List.iteri (fun i s -> Hashtbl.add sid_to_state s.sid i) stmts;

    let state_of (s : stmt) : int = Hashtbl.find sid_to_state s.sid in
    let end_state = List.length stmts in

    let succ_or_end (s : stmt) : int =
      match s.succs with
      | [t] -> state_of t
      | _ -> end_state
    in

    let cases =
      stmts |> List.map (fun s ->
        match s.skind with
        | Instr il ->
            let body = [mkStmt (Instr il); mk_set_state (succ_or_end s)] in
            mk_case_from_body (state_of s) body true
        | Return _ ->
            let body = [s] in
            mk_case_from_body (state_of s) body false
        | If (e, tb, fb, ifloc) ->
            let (t_s, f_s) = resolve_if_targets s tb fb in
            let then_block = mkBlock [mk_set_state (state_of t_s)] in
            let else_block = mkBlock [mk_set_state (state_of f_s)] in
            let ifs = mkStmt (If (e, then_block, else_block, ifloc)) in
            mk_case_from_body (state_of s) [ifs] true
        | Goto (tref, _) ->
            let target = !tref in
            let body = [mk_set_state (state_of target)] in
            mk_case_from_body (state_of s) body true
        | Break _ | Continue _ | Block _ | Loop _ ->
            let body = [mk_set_state (succ_or_end s)] in
            mk_case_from_body (state_of s) body true
        | _ ->
            let body = [mk_set_state end_state] in
            mk_case_from_body (state_of s) body true
      )
    in

    let end_label_stmt = mkStmt (Instr []) in
    end_label_stmt.labels <- [Label ("__end_flat", loc, false)];

    let exit_case =
      let s = mkStmt (Goto (ref end_label_stmt, loc)) in
      s.labels <- [Case (integer end_state, loc)];
      s
    in

    let entry_stmt = List.hd fd.sbody.bstmts in
    let init_state =
      let lv = Var state_vi, NoOffset in
      let i = Set (lv, integer (state_of entry_stmt), loc) in
      mkStmt (Instr [i])
    in

    let switch_stmt =
      mkStmt (Switch (Lval (Var state_vi, NoOffset),
                      mkBlock (cases @ [exit_case]),
                      [], loc))
    in

    let loop_stmt =
      mkStmt (Loop (mkBlock [switch_stmt], loc, None, None))
    in

    fd.sbody <- mkBlock [init_state; loop_stmt; end_label_stmt];

  end

class flattener = object
  inherit nopCilVisitor
  method! vfunc (fd : fundec) =
    flatten fd;
    DoChildren
end

let run (file : file) : unit =
  visitCilFileSameGlobals (new flattener) file

