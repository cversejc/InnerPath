"""Local, labelled synthetic case; generation/checks use the actual model.

The drain command never signs a node. Consultants review and sign through the UI.
Credentials are written only to the requested private artifact directory.
"""
import argparse
import asyncio
import json
import secrets
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import app
from app.config import settings
from app.db.session import AsyncSessionLocal, engine
from app.core.security import get_password_hash
from app.core.time import utc_now_naive
from app.models.user import User
from app.application.report_cases import create_user_service_request
from app.domains.service_requests.schemas import ServiceRequestCreate
from app.domains.service_requests.staff import accept_service_request
from app.domains.workflow.models import ReportCase, StepTask, WorkflowOutbox
from app.domains.skills.models import SkillRun
from app.domains.review.models import NodeReviewCommand
from app.application.node_review_workspace import review_workspace
from app.application.node_review_commands import queue_review_command
from app.domains.review.schemas import ReviewCommandInput
from app.tasks.workflow_tasks import _consume_outbox_event
from tools.run_framework_acceptance import sample_input
from tools.seed_collaboration_acceptance import require_local_database
from sqlalchemy import select


def save(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


async def seed(directory):
    require_local_database()
    data = sample_input("normal")
    data["profile"]["name"] = "合成整体审核验收用户"
    accounts = []
    async with AsyncSessionLocal() as db:
        demo_roles = [
            ("user", None, "合成整体审核验收用户"),
            ("consultant", "integrated", "整体审核演示综合咨询师"),
            ("admin", None, "整体审核演示管理员"),
        ]
        for role, specialty, name in demo_roles:
            phone="199"+"".join(str(secrets.randbelow(10)) for _ in range(8))
            password=secrets.token_urlsafe(18)
            user=User(phone=phone,name=name,role=role,consultant_type=specialty,password_hash=get_password_hash(password),is_active=True,**{k:v for k,v in data["profile"].items() if k in {"gender","birth_year","birth_month","birth_day","birth_hour","birth_minute","birth_time_precision","birth_place","calendar_type"}})
            db.add(user)
            await db.flush()
            accounts.append({"id":user.id,"phone":phone,"password":password,"role":role,"specialty":specialty})
        await db.commit()
        user=await db.get(User,accounts[0]["id"])
        request,case=await create_user_service_request(db,user,ServiceRequestCreate(service_type="report",profile=data["profile"],context=data["context"],idempotency_key=f"whole-node-real-model-{secrets.token_hex(8)}"))
        await db.commit()
        consultant = next(account for account in accounts if account["role"] == "consultant")
        await accept_service_request(db, request.id, await db.get(User, consultant["id"]))
        metadata={"case_id":case.id,"request_id":request.id,"accounts":accounts,"synthetic":True,"model_mode":"actual configured provider","created_at":utc_now_naive().isoformat()}
        save(directory/"private-case.json",metadata)
        save(directory/"request-snapshot.json",case.application_snapshot)
        print(json.dumps({"case_id":case.id,"request_id":request.id,"consultant_id":consultant["id"]}))


async def drain(directory, limit, *, quiet=False):
    require_local_database()
    metadata=json.loads((directory/"private-case.json").read_text(encoding="utf-8"))
    case_id=metadata["case_id"]
    processed=0
    for _ in range(limit):
        async with AsyncSessionLocal() as db:
            case=await db.get(ReportCase,case_id)
            steps=set(await db.scalars(select(StepTask.id).where(StepTask.workflow_instance_id==case.workflow_instance_id)))
            runs=set(await db.scalars(select(SkillRun.id).where(SkillRun.report_case_id==case_id)))
            commands=set(await db.scalars(select(NodeReviewCommand.id).where(NodeReviewCommand.report_case_id==case_id)))
            events=list(await db.scalars(select(WorkflowOutbox).where(WorkflowOutbox.status=="PENDING").order_by(WorkflowOutbox.id)))
            event=next((e for e in events if (e.payload_json or {}).get("report_case_id")==case_id or (e.payload_json or {}).get("step_task_id") in steps or (e.payload_json or {}).get("skill_run_id") in runs or (e.payload_json or {}).get("command_id") in commands),None)
            if not event:
                if not quiet:
                    print("No pending events for this acceptance case",flush=True)
                break
            event.status="PUBLISHED"
            event.published_at=utc_now_naive()
            await db.commit()
            event_id=event.id
        started=time.monotonic()
        result=await _consume_outbox_event(event_id)
        elapsed=round(time.monotonic()-started,2)
        with (directory/"operations.jsonl").open("a",encoding="utf-8") as log:
            log.write(json.dumps({"operation":"outbox_consume","event_id":event_id,"elapsed_seconds":elapsed,"result":result},ensure_ascii=False)+"\n")
        print(json.dumps({"event_id":event_id,"elapsed_seconds":elapsed,"result":result}),flush=True)
        processed += 1
    return processed


async def watch(directory, limit, poll_seconds, idle_timeout_seconds):
    last_activity=time.monotonic()
    while True:
        processed=await drain(directory,limit,quiet=True)
        if processed:
            last_activity=time.monotonic()
        elif idle_timeout_seconds > 0 and time.monotonic()-last_activity >= idle_timeout_seconds:
            print("Local case watcher idle timeout reached",flush=True)
            break
        await asyncio.sleep(poll_seconds)


async def snapshot(directory):
    metadata=json.loads((directory/"private-case.json").read_text(encoding="utf-8"))
    async with AsyncSessionLocal() as db:
        case=await db.get(ReportCase,metadata["case_id"])
        steps=list(await db.scalars(select(StepTask).where(StepTask.workflow_instance_id==case.workflow_instance_id).order_by(StepTask.sequence_no)))
        current=next((s for s in steps if s.status in {"READY","IN_REVIEW"}),steps[-1])
        account=next(a for a in metadata["accounts"] if a["role"] == "consultant" and a["specialty"] == "integrated")
        actor=await db.get(User,account["id"])
        review=await review_workspace(db,case.id,current.step_key,actor)
        save(directory/f"{current.step_key}-review.json",review)
        print(json.dumps({"case_id":case.id,"status":case.status,"step":current.step_key,"step_status":current.status,"can_approve":review["can_approve"],"issues":[{"type":i["type"],"severity":i["severity"],"message":i.get("message")} for i in review["issues"]],"commands":[{"id":c["id"],"kind":c["kind"],"status":c["status"],"error":c["error"]} for c in review["commands"]]},ensure_ascii=False))


async def retry(directory):
    metadata=json.loads((directory/"private-case.json").read_text(encoding="utf-8"))
    async with AsyncSessionLocal() as db:
        case=await db.get(ReportCase, metadata["case_id"])
        current=await db.scalar(select(StepTask).where(StepTask.workflow_instance_id==case.workflow_instance_id, StepTask.status=="IN_REVIEW").order_by(StepTask.sequence_no))
        actor=await db.get(User, current.assignee_id)
        review=await review_workspace(db,case.id,current.step_key,actor)
        command=await queue_review_command(db,case.id,current.step_key,actor,ReviewCommandInput(fingerprint=review["fingerprint"],idempotency_key=f"acceptance-retry:{secrets.token_hex(8)}"),"PREPARE")
        print(json.dumps({"command_id":command.id,"step":current.step_key,"status":command.status}))


async def inspect_runs(directory):
    metadata=json.loads((directory/"private-case.json").read_text(encoding="utf-8"))
    async with AsyncSessionLocal() as db:
        runs=list(await db.scalars(select(SkillRun).where(SkillRun.report_case_id==metadata["case_id"]).order_by(SkillRun.id)))
        for run in runs:
            save(directory/f"run-{run.id}.json", {"id":run.id,"status":run.status,"error":run.error,"trace":run.model_trace,"output":run.output_parsed,"raw":run.output_raw})
        print(json.dumps([{"id":r.id,"status":r.status,"error":r.error,"trace":r.model_trace} for r in runs], ensure_ascii=False))


async def main(args):
    args.directory.mkdir(parents=True,exist_ok=True)
    if args.operation=="seed": await seed(args.directory)
    elif args.operation=="drain": await drain(args.directory,args.limit)
    elif args.operation=="watch": await watch(args.directory,args.limit,args.poll_seconds,args.idle_timeout_seconds)
    elif args.operation=="retry": await retry(args.directory)
    elif args.operation=="runs": await inspect_runs(args.directory)
    else: await snapshot(args.directory)
    await engine.dispose()


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("operation",choices=["seed","drain","snapshot","retry","runs","watch"])
    parser.add_argument("--directory",type=Path,required=True)
    parser.add_argument("--limit",type=int,default=100)
    parser.add_argument("--poll-seconds",type=float,default=2)
    parser.add_argument("--idle-timeout-seconds",type=int,default=7200)
    asyncio.run(main(parser.parse_args()))
