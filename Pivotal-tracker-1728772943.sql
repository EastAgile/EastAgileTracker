CREATE TABLE IF NOT EXISTS "story_type" (
	"story_type_id" serial NOT NULL UNIQUE,
	"story_type_order" bigint NOT NULL,
	"story_type_name" varchar(255) NOT NULL,
	"story_type_desc" varchar(255) NOT NULL,
	"story_type_icon" varchar(255) NOT NULL,
	"allow_points" boolean NOT NULL,
	PRIMARY KEY ("story_type_id")
);

CREATE TABLE IF NOT EXISTS "project" (
	"project_id" serial NOT NULL UNIQUE,
	"owner_member_id" bigint NOT NULL,
	"effort_scale_id" jsonb NOT NULL,
	"priority_scale_id" bigint NOT NULL,
	"project_title" varchar(255) NOT NULL,
	"project_desc" varchar(255) NOT NULL,
	"account_id" bigint NOT NULL,
	"enable_tasks" boolean NOT NULL,
	"public_access" boolean NOT NULL,
	"public_url" varchar(255),
	"iteraction_start_day" bigint NOT NULL,
	"initial_velocity" double precision NOT NULL,
	"velocity_strategy" varchar(255),
	"iterations_to_show" bigint,
	"auto_plan" boolean,
	"allow_api_access" boolean,
	"enable_incoming_email" boolean,
	"hide_email_address" boolean,
	"priority_allowed" boolean,
	"priority_only_in_icebox" bigint,
	"points_for_bugs_chores" bigint,
	"created" timestamp with time zone NOT NULL,
	"expired" timestamp with time zone NOT NULL,
	PRIMARY KEY ("project_id")
);

CREATE TABLE IF NOT EXISTS "member" (
	"member_id" serial NOT NULL UNIQUE,
	"member_name" varchar(255) NOT NULL,
	"member_contact_id" bigint NOT NULL,
	"member_userid" varchar(255) NOT NULL,
	"created" timestamp with time zone NOT NULL,
	"expired" timestamp with time zone NOT NULL,
	"member_icon" varchar(255) NOT NULL,
	"member_initials" varchar(255) NOT NULL,
	PRIMARY KEY ("member_id")
);

CREATE TABLE IF NOT EXISTS "account" (
	"account_id" serial NOT NULL UNIQUE,
	PRIMARY KEY ("account_id")
);

CREATE TABLE IF NOT EXISTS "effort_scale" (
	"effort_scale_id" serial NOT NULL UNIQUE,
	"scale_name" varchar(255) NOT NULL,
	PRIMARY KEY ("effort_scale_id")
);

CREATE TABLE IF NOT EXISTS "scale_value" (
	"scale_value_id" serial NOT NULL UNIQUE,
	"scale_id" bigint,
	"scale_value_name" varchar(255) NOT NULL,
	"scale_value_value" varchar(255) NOT NULL,
	"scale_value_unit_name" varchar(255) NOT NULL,
	"scale_value_desc" varchar(255) NOT NULL,
	PRIMARY KEY ("scale_value_id")
);

CREATE TABLE IF NOT EXISTS "project_has_story_type" (
	"project_id" serial NOT NULL UNIQUE,
	"story_type_id" bigint NOT NULL,
	PRIMARY KEY ("project_id")
);

CREATE TABLE IF NOT EXISTS "story" (
	"story_id" serial NOT NULL UNIQUE,
	"project_id" bigint NOT NULL,
	"story_state_id" bigint NOT NULL,
	"iteration_id" bigint,
	"story_url" varchar(255),
	"story_type_id" bigint NOT NULL,
	"priority_id" bigint NOT NULL,
	"scale_value_id" bigint NOT NULL,
	"requestor_member_id" bigint NOT NULL,
	"description" varchar(255) NOT NULL,
	"code" varchar(255) NOT NULL,
	"icebox" bigint NOT NULL,
	"started" timestamp with time zone,
	"created" timestamp with time zone NOT NULL,
	"expired" timestamp with time zone,
	PRIMARY KEY ("story_id")
);

CREATE TABLE IF NOT EXISTS "member_contact" (
	"contact_id" serial NOT NULL UNIQUE,
	"member_id" bigint NOT NULL,
	"id_type" varchar(255) NOT NULL,
	"contact_address" bigint NOT NULL,
	"created" timestamp with time zone NOT NULL,
	"expired" timestamp with time zone,
	PRIMARY KEY ("contact_id")
);

CREATE TABLE IF NOT EXISTS "story_has_follower" (
	"story_id" serial NOT NULL UNIQUE,
	"member_id" bigint NOT NULL,
	PRIMARY KEY ("story_id", "member_id")
);

CREATE TABLE IF NOT EXISTS "story_has_owner" (
	"story_id" serial NOT NULL UNIQUE,
	"member_id" bigint NOT NULL,
	PRIMARY KEY ("story_id", "member_id")
);

CREATE TABLE IF NOT EXISTS "blocker" (
	"blocker_id" serial NOT NULL UNIQUE,
	"story_id" bigint NOT NULL,
	"blocker_desc" varchar(255) NOT NULL,
	"blocker_display_order" bigint NOT NULL,
	"created" timestamp with time zone NOT NULL,
	"expired" timestamp with time zone,
	PRIMARY KEY ("blocker_id")
);

CREATE TABLE IF NOT EXISTS "story_has_label" (
	"story_id" serial NOT NULL UNIQUE,
	"label_id" bigint NOT NULL,
	PRIMARY KEY ("story_id")
);

CREATE TABLE IF NOT EXISTS "label" (
	"label_id" serial NOT NULL UNIQUE,
	"label_name" varchar(255) NOT NULL,
	"background_color_hex" varchar(255) NOT NULL,
	"text_color_hex" varchar(255) NOT NULL,
	PRIMARY KEY ("label_id")
);

CREATE TABLE IF NOT EXISTS "priority" (
	"priority_id" serial NOT NULL UNIQUE,
	"priority_scale_id" bigint NOT NULL,
	"priority_name" varchar(255) NOT NULL,
	"priority_value_order" double precision NOT NULL,
	"priority_display_order" double precision NOT NULL,
	PRIMARY KEY ("priority_id")
);

CREATE TABLE IF NOT EXISTS "priority_scale" (
	"priority_scale_id" serial NOT NULL UNIQUE,
	"priority_scale_name" varchar(255) NOT NULL,
	PRIMARY KEY ("priority_scale_id")
);

CREATE TABLE IF NOT EXISTS "task" (
	"task_id" serial NOT NULL UNIQUE,
	"story_id" bigint NOT NULL,
	"task_desc" varchar(255) NOT NULL,
	"task_order" double precision NOT NULL,
	"created" timestamp with time zone NOT NULL,
	"expired" timestamp with time zone,
	PRIMARY KEY ("task_id")
);

CREATE TABLE IF NOT EXISTS "story_comment" (
	"story_comment_id" serial NOT NULL UNIQUE,
	"comment_text" varchar(255),
	"story_id" bigint,
	"comment_emoji" varchar(255),
	"created" timestamp with time zone NOT NULL,
	"expired" timestamp with time zone,
	PRIMARY KEY ("story_comment_id")
);

CREATE TABLE IF NOT EXISTS "epic_comment_has_mention" (
	"epic_comment_id" serial NOT NULL UNIQUE,
	"member_id" bigint NOT NULL,
	PRIMARY KEY ("epic_comment_id", "member_id")
);

CREATE TABLE IF NOT EXISTS "story_state_type" (
	"story_state_id" serial NOT NULL UNIQUE,
	"story_state_order" double precision NOT NULL,
	"story_state_name" varchar(255) NOT NULL,
	"story_state_desc" varchar(255) NOT NULL,
	"state_icon" varchar(255) NOT NULL,
	"started_state" boolean NOT NULL,
	"done_state" bigint NOT NULL,
	PRIMARY KEY ("story_state_id")
);

CREATE TABLE IF NOT EXISTS "project_has_story_state" (
	"story_state_id" serial NOT NULL UNIQUE,
	"project_id" bigint NOT NULL,
	PRIMARY KEY ("story_state_id")
);

CREATE TABLE IF NOT EXISTS "epic" (
	"epic_id" serial NOT NULL UNIQUE,
	"label_id" bigint NOT NULL,
	"epic_title" varchar(255) NOT NULL,
	"epic_desc" varchar(255),
	"epic_code" varchar(255),
	"epic_url" varchar(255),
	PRIMARY KEY ("epic_id")
);

CREATE TABLE IF NOT EXISTS "epic_comment" (
	"epic_comment_id" serial NOT NULL UNIQUE,
	"comment_text" varchar(255),
	"epic_id" bigint,
	"comment_emoji" varchar(255),
	"created" timestamp with time zone NOT NULL,
	"expired" timestamp with time zone,
	PRIMARY KEY ("epic_comment_id")
);

CREATE TABLE IF NOT EXISTS "story_comment_has_mention" (
	"story_comment_id" serial NOT NULL UNIQUE,
	"member_id" bigint NOT NULL,
	PRIMARY KEY ("story_comment_id", "member_id")
);

CREATE TABLE IF NOT EXISTS "epic_has_follower" (
	"epic_id" serial NOT NULL UNIQUE,
	"member_id" bigint NOT NULL,
	PRIMARY KEY ("epic_id", "member_id")
);

CREATE TABLE IF NOT EXISTS "iteration" (
	"iteration_id" serial NOT NULL UNIQUE,
	"project_id" bigint NOT NULL,
	"start" timestamp with time zone NOT NULL,
	"end" timestamp with time zone,
	PRIMARY KEY ("iteration_id")
);

CREATE TABLE IF NOT EXISTS "workspace" (
	"workspace_id" serial NOT NULL UNIQUE,
	"workspace_name" varchar(255) NOT NULL,
	"workspace_icon" varchar(255),
	PRIMARY KEY ("workspace_id")
);


ALTER TABLE "project" ADD CONSTRAINT "project_fk1" FOREIGN KEY ("owner_member_id") REFERENCES "member"("member_id");

ALTER TABLE "project" ADD CONSTRAINT "project_fk2" FOREIGN KEY ("effort_scale_id") REFERENCES "effort_scale"("effort_scale_id");

ALTER TABLE "project" ADD CONSTRAINT "project_fk3" FOREIGN KEY ("priority_scale_id") REFERENCES "priority_scale"("priority_scale_id");

ALTER TABLE "project" ADD CONSTRAINT "project_fk6" FOREIGN KEY ("account_id") REFERENCES "account"("account_id");



ALTER TABLE "scale_value" ADD CONSTRAINT "scale_value_fk1" FOREIGN KEY ("scale_id") REFERENCES "effort_scale"("effort_scale_id");
ALTER TABLE "project_has_story_type" ADD CONSTRAINT "project_has_story_type_fk0" FOREIGN KEY ("project_id") REFERENCES "project"("project_id");

ALTER TABLE "project_has_story_type" ADD CONSTRAINT "project_has_story_type_fk1" FOREIGN KEY ("story_type_id") REFERENCES "story_type"("story_type_id");
ALTER TABLE "story" ADD CONSTRAINT "story_fk1" FOREIGN KEY ("project_id") REFERENCES "project"("project_id");

ALTER TABLE "story" ADD CONSTRAINT "story_fk2" FOREIGN KEY ("story_state_id") REFERENCES "project_has_story_type"("story_type_id");

ALTER TABLE "story" ADD CONSTRAINT "story_fk3" FOREIGN KEY ("iteration_id") REFERENCES "iteration"("iteration_id");

ALTER TABLE "story" ADD CONSTRAINT "story_fk5" FOREIGN KEY ("story_type_id") REFERENCES "project_has_story_type"("story_type_id");

ALTER TABLE "story" ADD CONSTRAINT "story_fk6" FOREIGN KEY ("priority_id") REFERENCES "priority"("priority_id");

ALTER TABLE "story" ADD CONSTRAINT "story_fk7" FOREIGN KEY ("scale_value_id") REFERENCES "scale_value"("scale_value_id");

ALTER TABLE "story" ADD CONSTRAINT "story_fk8" FOREIGN KEY ("requestor_member_id") REFERENCES "member"("member_id");
ALTER TABLE "member_contact" ADD CONSTRAINT "member_contact_fk1" FOREIGN KEY ("member_id") REFERENCES "member"("member_id");
ALTER TABLE "story_has_follower" ADD CONSTRAINT "story_has_follower_fk0" FOREIGN KEY ("story_id") REFERENCES "story"("story_id");

ALTER TABLE "story_has_follower" ADD CONSTRAINT "story_has_follower_fk1" FOREIGN KEY ("member_id") REFERENCES "member"("member_id");
ALTER TABLE "story_has_owner" ADD CONSTRAINT "story_has_owner_fk0" FOREIGN KEY ("story_id") REFERENCES "story"("story_id");

ALTER TABLE "story_has_owner" ADD CONSTRAINT "story_has_owner_fk1" FOREIGN KEY ("member_id") REFERENCES "member"("member_id");
ALTER TABLE "blocker" ADD CONSTRAINT "blocker_fk1" FOREIGN KEY ("story_id") REFERENCES "story"("story_id");
ALTER TABLE "story_has_label" ADD CONSTRAINT "story_has_label_fk0" FOREIGN KEY ("story_id") REFERENCES "story"("story_id");

ALTER TABLE "story_has_label" ADD CONSTRAINT "story_has_label_fk1" FOREIGN KEY ("label_id") REFERENCES "label"("label_id");

ALTER TABLE "priority" ADD CONSTRAINT "priority_fk1" FOREIGN KEY ("priority_scale_id") REFERENCES "priority_scale"("priority_scale_id");

ALTER TABLE "task" ADD CONSTRAINT "task_fk1" FOREIGN KEY ("story_id") REFERENCES "story"("story_id");
ALTER TABLE "story_comment" ADD CONSTRAINT "story_comment_fk2" FOREIGN KEY ("story_id") REFERENCES "story"("story_id");
ALTER TABLE "epic_comment_has_mention" ADD CONSTRAINT "epic_comment_has_mention_fk0" FOREIGN KEY ("epic_comment_id") REFERENCES "epic_comment"("epic_comment_id");

ALTER TABLE "epic_comment_has_mention" ADD CONSTRAINT "epic_comment_has_mention_fk1" FOREIGN KEY ("member_id") REFERENCES "member"("member_id");

ALTER TABLE "project_has_story_state" ADD CONSTRAINT "project_has_story_state_fk0" FOREIGN KEY ("story_state_id") REFERENCES "story_state_type"("story_state_id");

ALTER TABLE "project_has_story_state" ADD CONSTRAINT "project_has_story_state_fk1" FOREIGN KEY ("project_id") REFERENCES "project"("project_id");
ALTER TABLE "epic" ADD CONSTRAINT "epic_fk1" FOREIGN KEY ("label_id") REFERENCES "label"("label_id");
ALTER TABLE "epic_comment" ADD CONSTRAINT "epic_comment_fk2" FOREIGN KEY ("epic_id") REFERENCES "epic"("epic_id");
ALTER TABLE "story_comment_has_mention" ADD CONSTRAINT "story_comment_has_mention_fk0" FOREIGN KEY ("story_comment_id") REFERENCES "story_comment"("story_comment_id");

ALTER TABLE "story_comment_has_mention" ADD CONSTRAINT "story_comment_has_mention_fk1" FOREIGN KEY ("member_id") REFERENCES "member"("member_id");
ALTER TABLE "epic_has_follower" ADD CONSTRAINT "epic_has_follower_fk0" FOREIGN KEY ("epic_id") REFERENCES "epic"("epic_id");

ALTER TABLE "epic_has_follower" ADD CONSTRAINT "epic_has_follower_fk1" FOREIGN KEY ("member_id") REFERENCES "member"("member_id");

